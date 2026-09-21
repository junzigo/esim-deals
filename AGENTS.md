::ILANG
[TYPE:instructions][PROJECT:esim-deals][LANG:zh]
::OBJECTIVE{维护英文美区旅行eSIM官方优惠静态站}
::STATE{@CONFIG, source:.ilang/site.ilang, role:配置唯一真源}
::RULE{只允许公开官方页面；先读robots；遇拒绝访问停止该源；不得绕过限制}
::RULE{纯Python标准库抓取构建；不依赖运行时AI或付费数据API}
::RULE{用户授权的Agent发现层使用锁定版本的官方MCP SDK；优惠抓取和静态数据生成仍为Python标准库；不使用付费服务}
::RULE{改配置后运行python -m unittest discover -s tests和python build.py}
::RULE{失效、过期、抓取失败的数据不冒充当前优惠；证据与日期必须可追溯}
::RULE{不承诺搜索排名、富媒体展示、收益或永久免费；不伪造年龄权重理论}
::RULE{允许维护源解析器、模板、测试、Actions与已授权Cloudflare部署}
::RULE{不得把令牌、私人信息或本机凭据上传仓库；联盟链接须经实际获批}
::BOUNDARY{never:编造 抄整篇文章 刷量 品牌词竞价 cookie注入 自买自推 付费升级|scope=permanent}
