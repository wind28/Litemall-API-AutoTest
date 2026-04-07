import requests
import pytest
import yaml
import pymysql
import logging

BASE_URL = "http://localhost:8080"


# ================= 数据库直连查询工具 =================
def query_db(sql):
    """连接 Docker MySQL 并执行查询，返回查询结果"""
    # Litemall 默认的数据库配置
    conn = pymysql.connect(
        host='127.0.0.1',
        port=3307,
        user='root',
        password='litemall123456',
        database='litemall',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()  # 获取所有查询到的数据
            return result
    finally:
        conn.close()



# ================= 1. 前置：全局登录 Fixture =================
@pytest.fixture(scope="session")
def admin_token():
    """这是一个前置夹具，会在所有测试开始前自动运行一次，拿到并返回 Token"""
    login_url = f"{BASE_URL}/admin/auth/login"
    login_data = {"username": "admin123", "password": "admin123"}

    res = requests.post(login_url, json=login_data)
    assert res.status_code == 200
    assert res.json()["errno"] == 0

    token = res.json()["data"]["token"]
    logging.info(f"\n[系统准备] 成功获取全局 Token: {token}")
    return token


# ================= 2. 读取YAML数据的辅助函数 =================
def get_yaml_data(file_path):
    """读取 YAML 文件并返回 Python 列表"""
    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data


# ================= 3. 数据驱动测试+数据库断言 (彻底解耦版) =================
@pytest.mark.parametrize("search_keyword", get_yaml_data("search_data.yaml"))
def test_search_goods(admin_token, search_keyword):
    """测试用例：搜索不同关键词的商品，并结合数据库进行双重断言"""
    goods_url = f"{BASE_URL}/admin/goods/list"
    headers = {"X-Litemall-Admin-Token": admin_token}
    params = {"name": search_keyword}

    # 1. 发起接口请求
    res = requests.get(goods_url, headers=headers, params=params)
    assert res.status_code == 200
    assert res.json()["errno"] == 0

    # 获取接口返回的商品总数
    api_total = res.json()["data"]["total"]

    # ================= 灵魂验证：去 MySQL 查底单 =================
    # 写一句 SQL：从 litemall_goods 表里模糊查询商品名字，且要求商品未被逻辑删除 (deleted=0)
    sql = f"SELECT count(*) as db_total FROM litemall_goods WHERE name LIKE '%{search_keyword}%' AND deleted = 0"
    db_result = query_db(sql)
    db_total = db_result[0]["db_total"]

    # 终极断言：接口查出来的数据量，必须和数据库里真实存在的数据量一模一样！
    assert api_total == db_total, f"数据不一致！接口显示 {api_total} 条，数据库显示 {db_total} 条"

    logging.info(
        f"\n[搜索测试] 关键词: '{search_keyword}', 接口查到 {api_total} 件, 数据库查到 {db_total} 件。数据强一致性校验通过！")


# ================= 4. 业务链路测试 (接口数据关联) =================
def test_goods_detail_chain(admin_token):
    """测试用例：业务链路连贯测试 (获取列表 -> 提取ID -> 查询详情)"""
    headers = {"X-Litemall-Admin-Token": admin_token}

    # ================= 步骤 1：查询商品列表 =================
    list_url = f"{BASE_URL}/admin/goods/list"
    res_list = requests.get(list_url, headers=headers)
    assert res_list.status_code == 200

    # 【核心技术动作：动态提取】从列表响应的 JSON 树中，精准挖出第一个商品的 ID 和 名称
    first_good_id = res_list.json()["data"]["list"][0]["id"]
    first_good_name = res_list.json()["data"]["list"][0]["name"]
    logging.info(f"\n[链路测试-步1] 成功从列表中提取到商品 ID: {first_good_id} (商品名: {first_good_name})")

    # ================= 步骤 2：拿着 ID 请求详情接口 =================
    detail_url = f"{BASE_URL}/admin/goods/detail"
    # 将提取到的 first_good_id 作为参数传给详情接口
    params = {"id": first_good_id}

    res_detail = requests.get(detail_url, headers=headers, params=params)
    assert res_detail.status_code == 200
    assert res_detail.json()["errno"] == 0

    # ================= 步骤 3：业务逻辑断言 =================
    # 提取详情接口返回的商品名称
    detail_name = res_detail.json()["data"]["goods"]["name"]

    # 终极断言：详情接口查出来的名字，必须等于在列表里看到的名字！
    assert detail_name == first_good_name, "链路数据不一致！"
    logging.info(f"[链路测试-步2] 详情接口调用成功！且名称匹配无误：{detail_name}")