import configparser
import sqlite3

from whoosh import scoring
from whoosh.index import open_dir
from whoosh.qparser import QueryParser, MultifieldParser, FuzzyTermPlugin

from datetime import datetime

from whoosh.query import Or, Wildcard


def get_user_preferences(user_id):
    # 定义数据库路径
    db_path = "../Data/user.db"
    # 连接到数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # 查询用户的偏好
    cursor.execute("SELECT like FROM user WHERE id=?", (user_id,))
    preferences = cursor.fetchone()
    conn.close()

    # 将偏好标签从字符串转换为列表，假设它们是以逗号分隔的
    if preferences and preferences[0]:
        return preferences[0].split(',')
    else:
        return []  # 如果没有找到用户或没有偏好，则返回空列表


def get_news_category(news_id):
    index_path = "../Data/index.db"
    conn = sqlite3.connect(index_path)
    cursor = conn.cursor()
    # 查询用户的偏好
    cursor.execute("SELECT category FROM web_pages WHERE id=?", (news_id,))
    category = cursor.fetchone()
    conn.close()

    return category


class Searcher:
    def __init__(self, config_path, config_encoding):
        # self.parser = Query('../config.ini', 'utf-8')
        self.config_path = config_path
        self.config_encoding = config_encoding
        config = configparser.ConfigParser()
        config.read(config_path, config_encoding)
        self.index_path = config['DEFAULT']['index_path']
        self.ix = open_dir(self.index_path)

    def search_index(self, query, query_text):
        with self.ix.searcher() as searcher:
            query_parser = QueryParser(query, schema=self.ix.schema)
            return query_parser.parse(query_text)

    def score(self, results, user_id=None):
        query_result = []
        for hit in results:
            result_dict = {
                'id': hit['id'],
                'page_rank': hit['page_rank'],
                'url': hit['url'],
                'title': hit['title'],
                'content': hit['pure_text'],
                'time': hit['time'],
                'score': hit.score
            }
            query_result.append(result_dict)

        max_bm25f_score = max(hit['score'] for hit in query_result)
        max_page_rank_score = max(hit['page_rank'] for hit in query_result)
        # 对每个结果调整得分
        for hit in query_result:
            if user_id:
                preferences = get_user_preferences(user_id)  # 获取用户偏好
                # 获取新闻类别
                category = get_news_category(hit['id'])
                # 提取第一个字符串
                category = category[0] if category else None

                # 然后使用提取的 category 字符串进行比较
                if category and category in preferences:
                    hit['score'] += 1  # 或其他适当的增量
                    # print(category)
            # 归一化并计算最终得分
            hit['score'] = hit['score'] / max_bm25f_score * 0.7 + hit['page_rank'] / max_page_rank_score * 0.3

        # 排序结果
        sorted_results = sorted(query_result, key=lambda x: x['score'], reverse=True)
        return sorted_results

    def basic_search(self, query, limit=1000, user_id=None):
        print('query:', query)

        with self.ix.searcher(weighting=scoring.BM25F) as searcher:
            query_parser = QueryParser("pure_text", schema=self.ix.schema)
            print(query)
            query = query_parser.parse(query)
            results = searcher.search(query, limit=limit)
            return self.score(results, user_id)

    # 任意字段查询
    def field_search(self, query_str, fields, limit=100):
        with self.ix.searcher(weighting=scoring.BM25F) as searcher:
            query_parser = MultifieldParser(fields, self.ix.schema)
            query = query_parser.parse(query_str)
            results = searcher.search(query, limit=limit)
            return self.score(results)

    # 完整短语查询
    def phrase_search(self, query_str, limit=100):
        with self.ix.searcher(weighting=scoring.BM25F) as searcher:
            query_parser = MultifieldParser(["pure_text"], self.ix.schema)
            query = query_parser.parse('"' + query_str + '"')
            results = searcher.search(query, limit=limit)
            return self.score(results)

    # 时间范围搜索

    def range_search(self, query_str, from_time, to_time, limit=100):
        with self.ix.searcher(weighting=scoring.BM25F) as searcher:
            from_time = datetime.strptime(from_time, "%Y-%m-%d")
            to_time = datetime.strptime(to_time, "%Y-%m-%d")

            # query = f"time:[{from_time.strftime('%Y-%m-%d ')} TO {to_time.strftime('%Y-%m-%d ')}] AND {query_str}"
            query = f"time:[{from_time.date()} TO {to_time.date()}] AND {query_str}"

            print(query)
            results = self.basic_search(query, limit=limit)
            return results

    # 模糊查询
    def fuzzy_search(self, query_str, limit=100):
        with self.ix.searcher(weighting=scoring.BM25F) as searcher:
            query = query_str + "~"  # 向搜索字符串添加波浪符号来表示模糊搜索
            query_parser = MultifieldParser(["pure_text"], self.ix.schema)
            query_parser.add_plugin(FuzzyTermPlugin())  # 添加模糊搜索插件
            query = query_parser.parse(query)
            results = searcher.search(query, limit=limit)
            return self.score(results)

    # 或逻辑查询
    def or_search(self, query_list, limit=100):
        with self.ix.searcher(weighting=scoring.BM25F) as searcher:
            query_parser = MultifieldParser(["pure_text"], self.ix.schema)

            # 创建OR查询对象
            or_query = Or([query_parser.parse(query) for query in query_list])
            results = searcher.search(or_query, limit=limit)
            return self.score(results)

    # 通配查询
    def wildcard_search(self, query_str, limit=100):
        with self.ix.searcher(weighting=scoring.BM25F) as searcher:
            query_parser = QueryParser("pure_text", schema=self.ix.schema, termclass=Wildcard)
            query = query_parser.parse(query_str)
            results = searcher.search(query, limit=limit)
            return self.score(results)


if __name__ == '__main__':
    search = Searcher('../config.ini', 'utf-8')
    from_time = "2003-11-30"
    to_time = "2023-11-30"
    # results = search.range_search("皇家马德里", from_time, to_time, 5)
    results = search.basic_search("足球", 100, 1)
    print('basic_search:')
    for result in results:
        print(result)
