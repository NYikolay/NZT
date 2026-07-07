# @log_domain_operation("test_search")
# async def test_search(session: AsyncSession, user_id, message: str):
#     connector = LLMConnector(api_key=settings.OPEN_ROUTER_API_KEY)
#
#     emb = await connector.get_llm_embedding(content=[message])
#
#     rep = EmbeddingRepository(session)
#
#     res = await rep.search_similar(
#         query_vector=emb[0].embedding,
#         embeddable_type=EmbeddableType.EVENTS,
#         user_id=user_id
#     )

