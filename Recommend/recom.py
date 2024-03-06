import sqlite3
import random
from collections import defaultdict
from operator import itemgetter

import math
import sqlite3
import dill as pickle


def get_titles_and_urls(db_path, page_ids):
    # 连接到SQLite数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 创建一部字典来保存结果
    results = {}
    for page_id in page_ids:
        # 执行查询语句
        cursor.execute("SELECT title, url FROM web_pages_copy1 WHERE id = ?", (page_id,))

        # 获取查询结果
        result = cursor.fetchone()
        if result:
            results[page_id] = {"title": result[0], "url": result[1]}

    # 关闭数据库连接
    conn.close()
    return results


def LoadDataFromSQLite(db_path, table_name, train_rate):
    # 连接到SQLite数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 执行查询语句
    cursor.execute(f"SELECT id, clicked_id FROM {table_name}")

    # 获取查询结果
    rows = cursor.fetchall()

    # 关闭数据库连接
    conn.close()

    train = []
    test = []
    random.seed(3)

    # 处理数据库查询结果
    for user_id, clicked_ids in rows:
        # 假设clicked_ids是以逗号分隔的字符串
        items = clicked_ids.split(',')
        for item in items:
            if random.random() < train_rate:
                train.append([int(user_id), item])
            else:
                test.append([int(user_id), item])

    return PreProcessData(train), PreProcessData(test)


def PreProcessData(originData):
    """
    建立User-Item表，结构如下：
        {"User1": {ClickedID1, ClickedID2, ClickedID3,...}
         "User2": {ClickedID12, ClickedID5, ClickedID8,...}
         ...
        }
    """
    trainData = defaultdict(set)
    for user, item in originData:
        trainData[user].add(item)
    return dict(trainData)


class ItemCF(object):
    """ Item based Collaborative Filtering Algorithm Implementation"""

    def __init__(self, similarity="cosine", norm=True):
        self._trainData = None
        self._similarity = similarity
        self._isNorm = norm
        self._itemSimMatrix = dict()  # 物品相似度矩阵

    def get_user_items(self, db_path, user_id, table_name):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(f"SELECT clicked_id FROM {table_name} WHERE id = ?", (user_id,))
            result = cursor.fetchone()
        finally:
            conn.close()

        # Ensure the result is not None and the first element is not an empty string
        if result and result[0]:
            # Split the string into a list, assuming it's a comma-separated string
            return result[0].split(',')
        else:
            # Return an empty list if no data is found or result is None
            return []

    def similarity(self):
        N = defaultdict(int)  # 记录每个物品的喜爱人数
        for user, items in self._trainData.items():
            for i in items:
                self._itemSimMatrix.setdefault(i, dict())
                N[i] += 1
                for j in items:
                    if i == j:
                        continue
                    self._itemSimMatrix[i].setdefault(j, 0)
                    if self._similarity == "cosine":
                        self._itemSimMatrix[i][j] += 1
                    elif self._similarity == "iuf":
                        self._itemSimMatrix[i][j] += 1. / math.log1p(len(items) * 1.)
        for i, related_items in self._itemSimMatrix.items():
            for j, cij in related_items.items():
                self._itemSimMatrix[i][j] = cij / math.sqrt(N[i] * N[j])
        # 是否要标准化物品相似度矩阵
        if self._isNorm:
            for i, relations in self._itemSimMatrix.items():
                max_num = relations[max(relations, key=relations.get)]
                # 对字典进行归一化操作之后返回新的字典
                self._itemSimMatrix[i] = {k: v / max_num for k, v in relations.items()}

    def recommend(self, user, N, K):
        """
        :param user: 被推荐的用户user
        :param N: 推荐的商品个数
        :param K: 查找的最相似的用户个数
        :return: 按照user对推荐物品的感兴趣程度排序的N个商品
        """
        items = self.get_user_items('../Data/user.db', user, 'user')
        recommends = dict()
        # 先获取user的喜爱物品列表

        for item in items:
            # 对每个用户喜爱物品在物品相似矩阵中找到与其最相似的K个
            for i, sim in sorted(self._itemSimMatrix.get(item, {}).items(), key=itemgetter(1), reverse=True)[:K]:
                if i in items:
                    continue  # 如果与user喜爱的物品重复了，则直接跳过
                recommends.setdefault(i, 0.)
                recommends[i] += sim
        # 根据被推荐物品的相似度逆序排列，然后推荐前N个物品给到用户
        return dict(sorted(recommends.items(), key=itemgetter(1), reverse=True)[:N])

    def train(self, trainData):
        self._trainData = trainData
        self.similarity()


# 在主函数中，你可以这样调用LoadDataFromSQLite
if __name__ == "__main__":
    db_path = "../Data/user.db"  # 替换为你的SQLite数据库文件路径
    table_name = "test"  # 替换为你的表名
    train, test = LoadDataFromSQLite(db_path, table_name, 1)
    print("train data size: %d, test data size: %d" % (len(train), len(test)))
    # 训练模型
    ItemCF = ItemCF(similarity='iuf', norm=True)
    ItemCF.train(train)

    # 保存模型
    with open('item_cf_model.pkl', 'wb') as f:
        pickle.dump(ItemCF, f)
