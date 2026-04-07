# Litemall接口自动化测试项目

这是我为了学习和实践接口自动化，基于开源电商系统Litemall编写的一个测试框架。主要串联了商城的几个核心业务接口，并加入了数据库的底层断言。

## 技术栈
- **Python 3.10**
- **Pytest** (测试框架与用例管理)
- **Requests** (接口调用)
- **PyMySQL** (直连数据库)
- **PyYAML** (测试数据驱动)
- **Allure** (测试报告生成)

## 项目实现细节
1. **测试数据解耦**：将搜索词等测试数据剥离到 `search_data.yaml` 文件中，通过 `@pytest.mark.parametrize` 动态读取，方便后期维护。
2. **全局鉴权前置**：使用Pytest的 `fixture(scope="session")` 机制接管登录动作，整个测试生命周期只登录一次，后续用例自动共享Token，提高了执行速度。
3. **接口数据关联**：实现了简单的业务链路闭环（先请求商品列表 -> 提取列表中第一个商品的ID-> 将ID传给商品详情接口进行校验）。
4. **数据库一致性断言**：在调完搜索接口后，代码会通过PyMySQL直接连入Docker里的MySQL查底单，跟接口返回的JSON数量做对比，防止接口“假成功”。

## 如何运行
1. **环境准备**：
   项目运行前，需确保本地（或WSL Docker）已启动Litemall后端服务及MySQL容器。
2. **修改配置**：
   由于脱敏原因，运行前请进入 `test_litemall_api.py`，将 `query_db` 函数中的MySQL密码修改为本地的真实密码。
3. **执行命令**：
   在终端执行以下命令运行测试并生成Allure报告：
   ```bash
   pytest -s test_litemall_api.py --alluredir=./allure-results
   allure serve ./allure-results
