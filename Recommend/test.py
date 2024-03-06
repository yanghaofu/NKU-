import dill as pickle
import random
from collections import defaultdict
from operator import itemgetter
import sqlite3
from Recommend.recom import get_titles_and_urls

# 加载模型
with open('item_cf_model.pkl', 'rb') as f:
    ItemCF = pickle.load(f)

# 使用模型进行推荐
recommendations = ItemCF.recommend(1, 10, 10)

# print("用户ID：", 1)
#
# 提取出电影ID
movie_ids = list(recommendations.keys())
print("推荐的新闻ID:", movie_ids)

# 连接到数据库并获取标题和URL
db_path = "../Data/index.db"  # 替换为你的SQLite数据库文件路径
titles_urls = get_titles_and_urls(db_path, movie_ids)

# 打印每个电影的标题和URL
for movie_id in movie_ids:
    if movie_id in titles_urls:
        print(f"新闻ID: {movie_id}, 标题: {titles_urls[movie_id]['title']}, URL: {titles_urls[movie_id]['url']}")
    else:
        print(f"新闻ID: {movie_id} 在数据库中未找到")
