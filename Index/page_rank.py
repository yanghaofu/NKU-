"""
PageRank calculated by default damping factor 0.9, max iterations 100, min delta 0.000001
"""

import networkx as nx
import sqlite3
import configparser
import matplotlib.pyplot as plt


class PageRankCalculator:
    config_path = ''
    config_encoding = ''
    db_path = ''

    def __init__(self, config_path, config_encoding):
        self.config_path = config_path
        self.config_encoding = config_encoding
        config = configparser.ConfigParser()
        config.read(config_path, config_encoding)
        self.db_path = config['DEFAULT']['db_path']

        self.damping_factor = 0.9  # alpha
        self.damping_value = 0  # (1-alpha)/N
        self.max_iterations = 100
        self.iteration_counter = 0
        self.min_delta = 0.000001
        self.graph = nx.DiGraph()

        self.con = sqlite3.connect(self.db_path)
        # 获取cursor对象
        self.cur = self.con.cursor()

        # 执行 SQL 查询语句，选择特定的列
        self.cur.execute("SELECT id, linkfrom FROM web_pages")

        # 获取查询结果
        result = self.cur.fetchall()

        # 构建字典
        self.id_linkfrom_dict = {}
        for row in result:
            id, linkfrom = row
            self.id_linkfrom_dict[id] = linkfrom

        # 打印字典
        # print(self.id_linkfrom_dict)

    def __del__(self):
        self.con.commit()
        self.con.close()

    def calculate_page_rank(self):  # add nodes and edges to graph. page rank init with -1. calculate page rank by
        # iteration
        # 创建一个图形对象
        # G = nx.Graph()
        for web_page, forward_list in self.id_linkfrom_dict.items():
            if forward_list is not None:
                forward_links = list(map(int, forward_list.split(',')))
            else:
                forward_links = []
            # forward_links = list(map(int, forward_list.split(',')))
            web_page_id = int(web_page)
            if web_page_id not in self.graph.nodes():
                self.graph.add_node(web_page_id, page_rank=0)
            for forward_link_id in forward_links:
                if forward_link_id not in self.graph.nodes() and forward_link_id is not None:
                    self.graph.add_node(forward_link_id, page_rank=0)
                self.graph.add_edge(forward_link_id, web_page_id)
        graph_size = len(self.graph.nodes())
        # # 绘制图形
        # pos = nx.spring_layout(self.graph)  # 选择布局算法
        # nx.draw(self.graph, pos, with_labels=True, node_size=300, node_color='skyblue', font_size=8, arrows=True)
        # plt.show()
        # print(self.graph.nodes())
        if not graph_size:
            print('graph size is 0. exit.')
            return
        self.damping_value = (1 - self.damping_factor) / graph_size
        for node in self.graph.nodes():
            self.graph.nodes[node]['page_rank'] = 1 / graph_size
            if self.graph.out_degree(node) == 0:  # if node has no out degree, add edges to all nodes.
                for another_node in self.graph.nodes():
                    self.graph.add_edge(node, another_node)
        for i in range(self.max_iterations):
            delta = self.iterate()
            self.iteration_counter += 1
            if delta < self.min_delta:
                break
        for node in self.graph.nodes():
            self.cur.execute('UPDATE web_pages SET page_rank = ? WHERE id = ?',
                             (self.graph.nodes[node]['page_rank'], node))
        print('page rank calculation finished. iteration: {}, delta: {}'.format(self.iteration_counter, delta))

    def iterate(self):
        delta = 0
        for node in self.graph.nodes():
            rank = 0
            for in_node in list(self.graph.in_edges(node)):
                in_node = in_node[0]
                rank += self.graph.nodes[in_node]['page_rank'] / self.graph.out_degree(in_node)
            rank = self.damping_value + self.damping_factor * rank
            delta = abs(self.graph.nodes[node]['page_rank'] - rank)
            self.graph.nodes[node]['page_rank'] = rank
        return delta


if __name__ == "__main__":
    calculator = PageRankCalculator('../config.ini', 'utf-8')
    calculator.calculate_page_rank()
