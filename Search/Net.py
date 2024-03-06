import datetime

from flask import Flask, render_template, request, redirect, jsonify, send_from_directory
import sqlite3
import os
from search import Searcher
import json
import dill as pickle
import random
from collections import defaultdict
from operator import itemgetter
from Recommend.recom import get_titles_and_urls

app = Flask(__name__)

# 配置SQLite数据库连接
DATABASE = '../Data/user.db'
db_path = '../Data/index.db'
log_path = '../Data/log.db'

global username
global password
global id
global title_id
global kind_id


# 注册新用户的函数
def register_user(username, password):
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS user (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    password TEXT NOT NULL,
                    like TEXT 
                    )''')

    cur.execute("INSERT INTO user (username, password) VALUES (?, ?)", (username, password))
    conn.commit()
    conn.close()


# 定义查询用户函数
def check_user(username, password):
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("SELECT * FROM user WHERE username=? AND password=?", (username, password))
    user = cur.fetchone()
    global id
    id = user[0]
    conn.close()
    # print(user)
    return user


def update_user_click_and_kind(db_path, user_id, title_id, cluster_num):
    user_id = int(user_id)  # 只有当您确定 user_id 可以安全转换为整数时才这么做
    # print(type(user_id))  # 检查 user_id 的类型
    print(title_id)
    print(cluster_num)

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # 获取现有的 clicked_id 和 kind_id
            cursor.execute("SELECT clicked_id, kind_id FROM user WHERE id=?", (user_id,))
            row = cursor.fetchone()
            if row:
                current_clicked_id, current_kind_id = row

                # 更新 clicked_id
                new_clicked_id = current_clicked_id + ',' + str(title_id) if current_clicked_id else str(title_id)

                # 更新 kind_id
                new_kind_id = current_kind_id + ',' + str(cluster_num) if current_kind_id else str(cluster_num)

                # 更新用户记录
                cursor.execute("UPDATE user SET clicked_id=?, kind_id=? WHERE id=?",
                               (new_clicked_id, new_kind_id, user_id))
                conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")


# 使用

def find_cluster_by_title_id(db_path, title_id):
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT cluster_num, books FROM cluster_data")
            rows = cursor.fetchall()

            for row in rows:
                cluster_num, books = row
                # 解析 books 字段（假设它是 JSON 格式的字符串）
                books = json.loads(books)
                if title_id in books:
                    return cluster_num
            return None  # 如果没有找到，返回 None
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None


@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('sign.html')


@app.route('/submit', methods=['POST'])
def submit():
    if request.method == 'POST':
        # 获取来自前端的 JSON 数据
        data = request.json
        global username
        global password
        # 提取数据
        username = data.get('username')
        password = data.get('password')
        action = data.get('action')
        if action == 'login':
            user = check_user(username, password)
            if user:
                response = {'message': 'Login successful', 'redirect': '/index'}
                return jsonify(response)
            else:
                response = {'message': 'Login fail'}
                return jsonify(response)
        elif action == 'register':
            # 假设注册成功后返回一个 JSON 响应
            register_user(username, password)
            response = {'message': 'Registration successful'}
            return jsonify(response)


@app.route('/index')
def index_page():
    return render_template('new.html')


@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')  # 获取查询参数
    # print(query)
    # 创建 Searcher 实例并执行搜索
    search = Searcher('../config.ini', 'utf-8')
    results = search.basic_search(query, 5, str(id))
    global db_path
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    formatted_results = []
    for result in results:
        cursor.execute("SELECT id FROM web_pages WHERE title=?", (result.get('title'),))
        row = cursor.fetchone()  # 假设只有一个匹配的ID

        if row:
            result_id = row[0]
            # 您可以在这里处理result_id，例如添加到结果字典中
            result['id'] = result_id

        formatted_result = {
            'id': result.get('id', 'N/A'),
            'page_rank': result.get('page_rank', 'N/A'),
            'url': result.get('url', 'N/A'),
            'title': result.get('title', 'N/A'),
            'content': result.get('content', 'N/A').strip().replace('\n', ' ')[0:200] + '...',  # 显示前200个字符
            'time': result.get('time', datetime.datetime.now()).strftime('%Y-%m-%d %H:%M:%S'),
            'score': result.get('score', 0)
        }
        formatted_results.append(formatted_result)

    # 记录查询到数据库
    conn = sqlite3.connect(log_path)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO search_log (query) VALUES (?)", (query,))
    conn.commit()
    conn.close()

    # 加载模型
    with open('../Recommend/item_cf_model.pkl', 'rb') as f:
        ItemCF = pickle.load(f)

    # 使用模型进行推荐
    recommendations = ItemCF.recommend(id, 10, 20)

    # 提取出电影ID
    movie_ids = list(recommendations.keys())

    # 连接到数据库并获取标题和URL
    db_path = "../Data/index.db"  # 替换为你的SQLite数据库文件路径
    titles_urls = get_titles_and_urls(db_path, movie_ids)

    recommended_items = []
    for title_id in movie_ids:
        if title_id in titles_urls:
            recommended_item = {
                'title': titles_urls[title_id]['title'],
                'url': titles_urls[title_id]['url']
            }
            recommended_items.append(recommended_item)

    print(recommended_items)
    # 将查询结果和推荐结果一起传递给模板
    return render_template('search_results.html', query=query, results=formatted_results,
                           recommendations=recommended_items)


@app.route('/Data/Code/<path:filename>')
def custom_static(filename):
    return send_from_directory('E:/大三/信息检索/hw_大作业/Project3/Data/Code', filename)


@app.route('/preferences')
def preferences():
    # 获取热门标签
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT tag FROM tags ORDER BY count DESC LIMIT 20")
    tags = [row[0] for row in cursor.fetchall()]
    conn.close()

    return render_template('preferences.html', tags=tags)


@app.route('/save_preferences', methods=['POST'])
def save_preferences():
    selected_tags = request.form.getlist('tags')  # 获取选中的标签
    # 将选中的标签保存到数据库
    global username  # 使用全局变量，根据实际情况可能需要调整
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("UPDATE user SET like=? WHERE username=?", (','.join(selected_tags), username))

    conn.commit()
    conn.close()

    return redirect('/index')


@app.route('/record_click', methods=['POST'])
def record_click():
    global id
    try:
        data = request.get_json()
        url = data.get('url')
        title = data.get('title')

        # 记录点击到数据库
        with sqlite3.connect(log_path) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO click_log (url, title) VALUES (?, ?)", (url, title))

        # 获取文章id
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM web_pages WHERE url=?", (url,))
            title_id = cursor.fetchone()[0]

        # 获取类别id
        kind_id = find_cluster_by_title_id(db_path, title_id)
        print(kind_id)

        # 记录点击到用户数据库
        update_user_click_and_kind(DATABASE, id, title_id, kind_id)

        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/logs')
def logs():
    conn = sqlite3.connect(log_path)
    cursor = conn.cursor()

    # 获取搜索日志
    cursor.execute("SELECT query, timestamp FROM search_log ORDER BY timestamp DESC")
    search_logs = cursor.fetchall()

    # 获取点击日志
    cursor.execute("SELECT url, title, timestamp FROM click_log ORDER BY timestamp DESC")
    click_logs = cursor.fetchall()

    conn.close()

    return render_template('logs.html', search_logs=search_logs, click_logs=click_logs)


@app.route('/advanced')
def advanced():
    return render_template('advanced_search.html')


@app.route('/advanced_search', methods=['GET', 'POST'])
def advanced_search():
    print(1)
    if request.method == 'POST':
        print(2)
        query_str = request.form.get('query')
        search_type = request.form.get('search_type')
        searcher = Searcher('../config.ini', 'utf-8')
        print(search_type, query_str)
        # 根据搜索类型调用不同的搜索方法
        if search_type == 'field_search':
            selected_fields = request.form.getlist('fields')  # 获取选中的字段
            results = searcher.field_search(query_str, selected_fields)
        elif search_type == 'phrase_search':
            results = searcher.phrase_search(query_str)
        elif search_type == 'range_search':
            from_time = request.form.get('from_time')
            to_time = request.form.get('to_time')
            results = searcher.range_search(query_str, from_time, to_time)
        elif search_type == 'or_search':
            query_list = [q.strip() for q in query_str.split(',')]
            # 执行or_search
            results = searcher.or_search(query_list)

        elif search_type == 'wildcard_search':
            results = searcher.wildcard_search(query_str)

        formatted_results = []
        for result in results:
            formatted_result = {
                'page_rank': result.get('page_rank', 'N/A'),
                'url': result.get('url', 'N/A'),
                'title': result.get('title', 'N/A'),
                'content': result.get('content', 'N/A').strip().replace('\n', ' ')[0:200] + '...',  # 显示前200个字符
                'time': result.get('time', datetime.datetime.now()).strftime('%Y-%m-%d %H:%M:%S'),
                'score': result.get('score', 0)
            }
            formatted_results.append(formatted_result)

        # 加载模型
        with open('../Recommend/item_cf_model.pkl', 'rb') as f:
            ItemCF = pickle.load(f)

        # 使用模型进行推荐
        recommendations = ItemCF.recommend(id, 10, 10)

        # 提取出电影ID
        movie_ids = list(recommendations.keys())

        # 连接到数据库并获取标题和URL
        db_path = "../Data/index.db"  # 替换为你的SQLite数据库文件路径
        titles_urls = get_titles_and_urls(db_path, movie_ids)

        recommended_items = []
        for title_id in movie_ids:
            if title_id in titles_urls:
                recommended_item = {
                    'title': titles_urls[title_id]['title'],
                    'url': titles_urls[title_id]['url']
                }
                recommended_items.append(recommended_item)

        # 将查询结果和推荐结果一起传递给模板
        return render_template('search_results.html', query=query_str, results=formatted_results,
                               recommendations=recommended_items)

    # GET请求，显示高级搜索表单
    return render_template('advanced_search.html')


if __name__ == '__main__':
    app.run(debug=True)
