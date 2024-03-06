import re
import string
import jieba
import pandas as pd
import sqlite3


class TextProcessor:
    def __init__(self, db_path='../Data/index.db', stopwords_path='cn_stopwords.txt'):
        self.db_path = db_path
        self.stopwords_path = stopwords_path
        self.stopword_list = self.load_stopwords()

    def load_stopwords(self):
        with open(self.stopwords_path, encoding="utf8") as f:
            return f.readlines()

    def tokenize_text(self, text):
        tokens = jieba.lcut(text)
        tokens = [token.strip() for token in tokens]
        return tokens

    def remove_special_characters(self, text):
        tokens = self.tokenize_text(text)
        pattern = re.compile('[{}]'.format(re.escape(string.punctuation)))
        filtered_tokens = filter(None, [pattern.sub('', token) for token in tokens])
        filtered_text = ' '.join(filtered_tokens)
        return filtered_text

    def remove_stopwords(self, text):
        tokens = self.tokenize_text(text)
        filtered_tokens = [token for token in tokens if token not in self.stopword_list]
        filtered_text = ''.join(filtered_tokens)
        return filtered_text

    def normalize_corpus(self, corpus):
        normalized_corpus = []
        for text in corpus:
            text = " ".join(jieba.lcut(text))
            normalized_corpus.append(text)
        return normalized_corpus

    def process_text_from_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, content FROM web_pages_copy1")
        contents = cursor.fetchall()
        conn.close()

        processed_data = []
        for row in contents:
            record = {
                'id': row[0],
                'title': row[1],
                'content': self.remove_stopwords(self.remove_special_characters(row[2]))
            }
            processed_data.append(record)

        return pd.DataFrame(processed_data)


processor = TextProcessor()
processed_df = processor.process_text_from_db()

# 保存到 CSV 文件
processed_df.to_csv('processed_text_data.csv', index=False)

