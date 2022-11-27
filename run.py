#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import datetime
import time
import os
import json
import traceback
import time
import re
import requests

requests.packages.urllib3.disable_warnings()


class GithubClient:

    def __init__(self, token):
        self.url = 'https://api.github.com'
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Connection': 'close',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.119 Safari/537.36'
        }
        self.limit = 0
        self.users_octocat()

    def connect(self, method, resource, data=None):
        '''访问api'''
        time.sleep(0.1)
        if method == 'GET':
            r = requests.get('{0}{1}'.format(
                self.url, resource), params=data, headers=self.headers, verify=False, allow_redirects=False)
        elif method == 'POST':
            r = requests.post('{0}{1}'.format(
                self.url, resource), data=data, headers=self.headers, verify=False, allow_redirects=False)
        r.encoding = r.apparent_encoding
        if 'X-RateLimit-Remaining' in r.headers.keys():
            self.limit = int(r.headers['X-RateLimit-Remaining'])
        try:
            return r.status_code, r.headers, r.json()
        except:
            return r.status_code, r.headers, r.content

    def search_code(self, keyword, page=1, per_page=10):
        '''搜索代码'''
        try:
            time.sleep(2)
            data = {'q': keyword, 'sort': 'indexed',
                    'order': 'desc', 'page': page, 'per_page': per_page}
            _, _, rs = self.connect("GET", '/search/code', data=data)
            return rs
        except:
            return {}

    def repos(self, author, repo):
        '''项目信息'''
        try:
            _, _, rs = self.connect("GET", f'/repos/{author}/{repo}')
            return rs
        except:
            return {}

    def repos_commits(self, author, repo):
        '''项目commit信息'''
        try:
            _, _, rs = self.connect(
                "GET", f'/repos/{author}/{repo}/commits')
            if isinstance(rs, dict):
                if rs.get('message', '') == 'Moved Permanently' and 'url' in rs:
                    _, _, rs1 = self.connect("GET", rs['url'][18:])
                    if isinstance(rs1, list):
                        return rs1
            elif isinstance(rs, list):
                return rs
        except:
            pass
        return []

    def repos_releases_latest(self, author, repo):
        '''项目最新release'''
        try:
            _, _, rs = self.connect(
                "GET", f'/repos/{author}/{repo}/releases/latest')
            return rs
        except:
            return {}

    def users_octocat(self):
        '''检查速率限制'''
        try:
            _, _, _ = self.connect(
                "GET", '/users/octocat')
        except:
            pass


# 保存数据
data = {}
data_file = 'data.json'

# 项目清单
with open('repos.md', 'r', encoding='utf8') as fr:
    repos = fr.readlines()
    for repo in repos[2:]:
        if '|' in repo:
            try:
                type_1, type_2, url = repo.split('|')[1:4]
            except:
                print(f'[repo error] {repo}')
                continue
            if len(url[19:].split('/', 1)) != 2:
                print(f'[url error] {url}')
                continue
            data.setdefault(type_1, {})
            data[type_1].setdefault(type_2, {})
            data[type_1][type_2].setdefault(url, {})
        # break

# 更新数据
gc = GithubClient(os.getenv('GH_TOKEN'))
for type_1 in data:
    for type_2 in data[type_1]:
        for url in data[type_1][type_2]:
            if gc.limit > 0:
                print(f'[{gc.limit}] {url}')
            else:
                continue
            author, repo = url[19:].split('/', 1)
            item = data[type_1][type_2][url]
            try:
                rs1 = gc.repos(author, repo)
                item['created_at'] = time.strftime("%Y-%m-%d %H:%M:%S", time.strptime(
                    rs1['created_at'], "%Y-%m-%dT%H:%M:%SZ")) if rs1.get('created_at') else ''
                item['description'] = rs1.get('description')
                rs2 = gc.repos_commits(author, repo)
                for rs in rs2[:1]:
                    item['commit_date'] = time.strftime("%Y-%m-%d %H:%M:%S", time.strptime(
                        rs['commit']['committer']['date'], "%Y-%m-%dT%H:%M:%SZ")) if rs['commit']['committer']['date'] else ''
                    item['commit_message'] = rs['commit']['message'] if rs['commit']['message'] else ''
                rs3 = gc.repos_releases_latest(author, repo)
                item['release_tag'] = rs3.get('tag_name')
                item['release_date'] = time.strftime("%Y-%m-%d %H:%M:%S", time.strptime(
                    rs3['published_at'], "%Y-%m-%dT%H:%M:%SZ")) if rs3.get('published_at') else ''
                item['release_message'] = rs3.get('body')
            except:
                print('[fail 1]', url)
                traceback.print_exc()

# 更新README.md
n = 1000

release_md = f'''
## 近{n}天release更新记录
| 项目名称 | 更新时间 | 版本 | 更新内容 |
| :---- | :---- | :---- | :---- |
'''

commit_md = f'''
## 近{n}天commit提交记录
| 项目名称 | 提交时间 | 更新内容 |
| :---- | :---- | :---- |
'''

total_md = '## 所有项目\n'
def split(x, y): return [x[i:i+y] for i in range(0, len(x), y)]


def parse(x, y): return "<br>".join(split(re.sub('\s+', '', x), y))


for type_1 in data:
    total_md += f'### {type_1}\n'
    for type_2 in data[type_1]:
        total_md += f'#### {type_2}\n| 项目名称/版本| 提交时间 | 项目描述 |\n| :---- | :---- | :---- |\n'
        for url in data[type_1][type_2]:
            print(f'[to_md] {url}')
            try:
                item = data[type_1][type_2][url]
                author, repo = url[19:].split('/', 1)
                created_at = item.get('created_at', '')
                description = parse(item.get('description', ''), 25)
                release_tag = item.get('release_tag', '')
                release_date = item.get('release_date', '')
                release_message = parse(item.get('release_message', ''), 20)
                commit_date = item.get('commit_date', '')
                commit_message = parse(item.get('commit_message', ''), 20)
                if release_date:
                    if time.mktime(time.strptime(release_date, "%Y-%m-%d %H:%M:%S")) > time.mktime((datetime.datetime.now() - datetime.timedelta(days=n)).timetuple()):
                        release_md += f'| [{repo}]({url}) | {release_date} | {release_tag} | {release_message} |\n'
                if commit_date:
                    if time.mktime(time.strptime(commit_date, "%Y-%m-%d %H:%M:%S")) > time.mktime((datetime.datetime.now() - datetime.timedelta(days=n)).timetuple()):
                        commit_md += f'| [{repo}]({url}) | {commit_date} | {commit_message} |\n'
                total_md += f'| [{repo}]({url}) {release_tag} | {commit_date} | {description} |\n'
            except:
                print(f'[fail 2] {url}')
                traceback.print_exc()

with open("README.md", 'w', encoding='utf8') as fd:
    fd.write("# 更新于 {}\n".format(time.strftime("%Y-%m-%d %H:%M:%S")) +
             release_md + commit_md + total_md)

# 写入data
with open(data_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)
