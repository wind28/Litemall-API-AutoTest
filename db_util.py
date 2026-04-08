import pymysql

def check_goods_in_db(goods_id):
    # 连接 Docker 里的 Litemall 数据库
    # 注意：这里的密码和端口取决于你 docker-compose.yml 里的配置
    db = pymysql.connect(
        host="127.0.0.1",
        user="litemall",       # 默认通常是 litemall
        password="litemall123", # 默认密码
        database="litemall",
        port=3306
    )
    cursor = db.cursor()
    # 根据 ID 去数据库查真实的底单
    sql = f"SELECT name FROM litemall_goods WHERE id = {goods_id} AND deleted = 0"
    cursor.execute(sql)
    result = cursor.fetchone()
    db.close()
    return result[0] if result else None