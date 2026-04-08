import logging
import requests
import pytest
import yaml
import pymysql

HOST = "http://localhost:8080"


def execute_sql(sql):
    # 连 docker 里的 mysql 测试库
    # TODO: 后续把账号密码抽离到 config 文件里，先写死方便跑通
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
            return cursor.fetchall()
    finally:
        conn.close()


@pytest.fixture(scope="session")
def get_admin_token():
    # 跑所有测试前先拿一次管理员 token
    url = f"{HOST}/admin/auth/login"
    body = {"username": "admin123", "password": "admin123"}

    res = requests.post(url, json=body)
    assert res.status_code == 200, "网络请求失败，检查后端服务是否挂了"
    assert res.json().get("errno") == 0, "登录失败，账号或密码错误"

    token = res.json()["data"]["token"]
    logging.info(f"拿到全局鉴权 token: {token}")
    return token


def load_test_data(yaml_file):
    with open(yaml_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        return data["search_cases"]


@pytest.mark.parametrize("case_data", load_test_data("search_data.yaml"))
def test_search_goods(get_admin_token, case_data):
    url = f"{HOST}/admin/goods/list"
    headers = {"X-Litemall-Admin-Token": get_admin_token}

    keyword = case_data["keyword"]

    # 1. 查接口
    res = requests.get(url, headers=headers, params={"name": keyword})
    assert res.status_code == case_data["http_status"]
    api_count = res.json()["data"]["total"]

    # 2. 查DB核对底单
    sql = f"SELECT count(*) as total FROM litemall_goods WHERE name LIKE '%{keyword}%' AND deleted = 0"
    db_count = execute_sql(sql)[0]["total"]

    # 发现数据不对时，报错信息要打印出具体的数字，方便查Bug
    assert api_count == db_count, f"搜索【{keyword}】数量对不上！接口返回{api_count}，数据库{db_count}"
    logging.info(f"搜索 {keyword} 测试OK，数量: {api_count}")


def test_goods_detail_chain(get_admin_token):
    headers = {"X-Litemall-Admin-Token": get_admin_token}

    # 先查列表，随便捞第一个商品拿来做下游请求的参数
    list_url = f"{HOST}/admin/goods/list"
    res_list = requests.get(list_url, headers=headers)
    assert res_list.status_code == 200

    target_item = res_list.json()["data"]["list"][0]
    item_id = target_item["id"]
    item_name = target_item["name"]
    logging.info(f"随机抽取的测试商品 -> id: {item_id}, name: {item_name}")

    # 带着刚才拿到的 ID 去请求详情接口
    detail_url = f"{HOST}/admin/goods/detail"
    res_detail = requests.get(detail_url, headers=headers, params={"id": item_id})
    assert res_detail.status_code == 200

    api_detail_name = res_detail.json()["data"]["goods"]["name"]
    assert api_detail_name == item_name, "列表查出来的名字和详情页对不上"

    # 终极校验：拿ID去数据库查到底叫啥
    sql = f"SELECT name FROM litemall_goods WHERE id = {item_id} AND deleted = 0"
    db_result = execute_sql(sql)
    db_name = db_result[0]["name"] if db_result else None

    assert api_detail_name == db_name, "接口数据跟DB底单不一致，可能有脏数据或缓存未更新！"
    logging.info("详情页链路 + 数据库底层校验通过")