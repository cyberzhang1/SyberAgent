# core/memory_manager.py
from neo4j import AsyncGraphDatabase
import json
from typing import List, Dict

from .config import settings
from .llm_client import async_client   # ① 从独立模块导入，避免循环依赖


class Neo4jMemoryManager:
    def __init__(self):
        self.driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )

    async def close(self):
        await self.driver.close()

    async def _execute_query(self, query, parameters=None):
        async with self.driver.session() as session:
            result = await session.run(query, parameters)
            return [record.data() for record in await result.list()]

    async def extract_and_store_triplets(self, text: str):
        """使用 LLM 从文本中提取三元组并存入 Neo4j"""
        prompt = f"""
        从以下文本中提取知识三元组（主语, 关系, 宾语）。
        请遵循以下规则：
        1. 主语和宾语应该是明确的实体（人名、地名、组织名、概念等）。
        2. 关系应该是描述性的动词或短语。
        3. 以 JSON 列表格式返回，每个元素是一个包含 'subject', 'relation', 'object' 键的字典。
        4. 如果没有可提取的信息，返回一个空列表。

        文本："{text}"
        """
        response = await async_client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        try:
            content = response.choices[0].message.content
            triplets_data = json.loads(content)
            triplets = triplets_data.get("triplets", [])   # ② 补全默认值

            if not isinstance(triplets, list):
                return

            for triplet in triplets:
                query = """
                MERGE (s:Entity {name: $subject})
                MERGE (o:Entity {name: $object})
                MERGE (s)-[:RELATION {type: $relation}]->(o)
                """
                await self._execute_query(
                    query,
                    parameters={
                        "subject": triplet.get("subject"),
                        "object": triplet.get("object"),
                        "relation": triplet.get("relation"),
                    }
                )
            print(f"Stored {len(triplets)} triplets in Neo4j.")
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Failed to parse or store triplets: {e}\nRaw LLM output: {content}")

    async def retrieve_context_for_prompt(self, prompt: str, top_k: int = 3) -> str:
        """根据用户提问，从知识图谱中检索相关上下文"""
        entity_extraction_prompt = (
            f"从以下问题中识别出核心实体（人、地点、组织等），"
            f"并以 JSON 列表格式返回：'{prompt}'"
        )
        response = await async_client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": entity_extraction_prompt}],
            response_format={"type": "json_object"}
        )

        try:
            entities_data = json.loads(response.choices[0].message.content)
            entities = entities_data.get("entities", [])   # ② 补全默认值
            if not entities:
                return ""

            context_parts: List[str] = []
            for entity in entities:
                query = """
                MATCH (n:Entity {name: $entity_name})-[r]-(m)
                RETURN n.name AS subject, type(r) AS relation, m.name AS object
                LIMIT $limit
                """
                results = await self._execute_query(
                    query,
                    parameters={"entity_name": entity, "limit": top_k}
                )
                for res in results:
                    context_parts.append(
                        f"{res['subject']} {res['relation']} {res['object']}."
                    )

            if not context_parts:
                return ""

            context_str = " ".join(set(context_parts))  # 去重
            return f"背景知识：{context_str}\n\n"

        except Exception as e:
            print(f"Failed to retrieve context from Neo4j: {e}")
            return ""


# 全局实例
memory_manager = Neo4jMemoryManager()