from search import Searcher

if __name__ == '__main__':
    searcher = Searcher('../config.ini', 'utf-8')
    results = searcher.phrase_search("皇家马德里", 5)
    for result in results:
        print(result)
    # indexer.search_index("皇家马德里")
