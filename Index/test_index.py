# from whoosh.qparser import QueryParser
# from index import Indexer
#
#
# def search_index(indexer, query_text):
#     with indexer.ix.searcher() as searcher:
#         query_parser = QueryParser("pure_text", schema=indexer.schema)
#         query = query_parser.parse(query_text)
#         results = searcher.search(query)
#         print(f"Total results found: {len(results)}")
#         for hit in results:
#             # f"Score: {hit.score}, URL: {hit['url']},
#             print(f"Title: {hit['title']}")
#             print("Content:", hit['pure_text'])
#             print("----")
#
#
# if __name__ == '__main__':
#     # 初始化 Indexer
#     indexer = Indexer('../config.ini', 'utf-8')
#     indexer.get_db()
#     # 执行搜索
#     search_index(indexer, "足球")
#
#
from whoosh.index import open_dir

index_path = "../Data/Index/"  # 修改为您的索引路径
ix = open_dir(index_path)
print(ix.schema)

ix = open_dir(index_path)
print("Document count:", ix.doc_count_all())
with ix.searcher() as searcher:
    # 获取所有词项
    terms = list(searcher.reader().all_terms())
    print("Total terms:", len(terms))

    # 打印前 100 个词项
    for term in terms[:100]:
        print(term)