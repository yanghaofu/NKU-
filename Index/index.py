import sqlite3
import configparser
import os
from datetime import datetime

from whoosh.index import create_in
from whoosh.fields import Schema, TEXT, ID, DATETIME, NUMERIC, KEYWORD
from jieba.analyse import ChineseAnalyzer


class Indexer:
    config_path = ''
    config_encoding = ''

    def __init__(self, config_path, config_encoding):
        self.rows_as_dict = None
        self.config_path = config_path
        self.config_encoding = config_encoding
        config = configparser.ConfigParser()
        config.read(config_path, config_encoding)
        self.db_path = config['DEFAULT']['db_path']
        self.index_path = config['DEFAULT']['index_path']

        self.analyzer = ChineseAnalyzer()
        self.schema = Schema(
            id=NUMERIC(unique=True, stored=True),
            url=TEXT(stored=True),
            title=TEXT(stored=True, analyzer=self.analyzer),
            pure_text=TEXT(stored=True, analyzer=self.analyzer),
            page_rank=NUMERIC(stored=True),
            time=DATETIME(stored=True),
            category=TEXT(stored=True, analyzer=self.analyzer)
        )

        if not os.path.exists(self.index_path):
            os.mkdir(self.index_path)
        self.ix = create_in(self.index_path, self.schema)
        self.writer = self.ix.writer()
        # self.page_rank_calculator = PageRankCalculator('../config.ini', 'utf-8')

        self.con = sqlite3.connect(self.db_path)
        # 获取cursor对象
        self.cur = self.con.cursor()

    def __del__(self):
        self.con.commit()
        self.con.close()

    def get_db(self):
        # 执行 SQL 查询语句，选择特定的列
        self.cur.execute("SELECT id, url, title, content, time, linkto, linkfrom, page_rank ,category FROM web_pages")
        result = self.cur.fetchall()

        # 创建一个空的字典，用于存储结果
        self.rows_as_dict = {}
        # 遍历每一行数据，将其转换为字典，并以id为键存储到rows_as_dict中
        for row in result:
            row_dict = {
                'url': row[1],
                'title': row[2],
                'content': row[3],
                'time': row[4],
                'linkto_num': row[5],
                'linkfrom_num': row[6],
                'page_rank': row[7],
                'category': row[8]
            }
            self.rows_as_dict[row[0]] = row_dict

        # 现在 rows_as_dict 是一个字典，以id为键，包含其他属性的字典为值

    def build_index(self):
        # 获取数据库数据并处理为适合索引的格式
        self.get_db()
        doc_counter = 0

        # 遍历 rows_as_dict，将数据添加到索引器中
        for doc_id, doc_data in self.rows_as_dict.items():
            # 将时间字符串转换为datetime对象
            doc_data['time'] = datetime.strptime(doc_data['time'], "%Y-%m-%d %H:%M:%S")
            # print(doc_data['time'])
            self.writer.add_document(
                id=doc_id,
                url=doc_data['url'],
                title=doc_data['title'],
                pure_text=doc_data['content'],
                page_rank=doc_data['page_rank'],
                time=doc_data['time'],
                category=doc_data['category']
            )
            # print(doc_data['title'])
            # print(doc_data['content'])
            doc_counter += 1

            self.writer.commit()
            self.writer = self.ix.writer()


if __name__ == '__main__':
    indexer = Indexer('../config.ini', 'utf-8')
    indexer.build_index()
    # 执行搜索
