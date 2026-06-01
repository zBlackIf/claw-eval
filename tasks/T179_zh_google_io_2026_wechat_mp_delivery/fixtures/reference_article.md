# 帮大家总结了一下凌晨的Google I/O 2026开发者大会。

刚刚，Google开完了他们的产品发布会。

回顾这半年，AI圈的热闹，几乎跟Google没啥关系。

但了解Google的人都知道，它就喜欢攒一波，然后在I/O大会上，一口气全放出来。

终于，今年的，又来了。

我也通宵给大家蹲完，然后整理完了。
可能会是最全的一篇了。

## 一. AI模型

### 1. Gemini 3.5 Flash

今年I/O大会的明星之一，Gemini 3.5 Flash。

一般来说，Flash系列是轻量快速版，主打便宜和快，Pro才是满血旗舰版。

但现在基本上都流行，新一代的小模型，要比上一代的大模型还要强，所以这次也是一样，3.5 Flash的能力在编码能力、Agent能力、工具调用能力都比上一代的3.1 Pro要强不少。

Terminal-Bench 2.1编码测试，3.5 Flash拿了76.2%，3.1 Pro只有70.3%。GDPval-AA，衡量真实世界经济价值任务的，3.5 Flash 1656 Elo，3.1 Pro 1314 Elo，差了三百多分。

跑分上确实强了不少。

不过呢，3.5 Flash在Humanity's Last Exam（人类最后考试）上40.2%，比3.1 Pro的44.4%差，ARC-AGI-2上72.1%也输给Pro的77.1%。

这两个benchmark主要考的是世界知识和纯抽象推理。

也就是说，这次也是牺牲了知识的能力，换来了干活的能力的加强。

输出速度方面，比其他前沿模型快4倍。

价格这块，输入$1.50/百万token，输出$9.00/百万token，比3 Flash贵了3倍，但比3.1 Pro便宜40%。

现在真的全网token提价真的是大势所趋。。。

然后知识截止日期到2025年1月（感觉拉了个大的），上下文窗口100万token。

至于Gemini 3.5 Pro，他们亲口说的是"Give us until next month to get it to you"，也就是下个月见。

3.5 Flash今天直接成为Gemini App和AI Mode in Search的默认模型，全球同步上线API、AI Studio、Antigravity等等，所有人也都可以去体验了。

### 2. Gemini Omini Flash

Gemini Omni，这个东西其实发布会之前就已经在推特上炒疯了。

说真的，其实是有点期待的。

毕竟，谷歌把这玩意称为"a new model that can create anything from any input"，也就是能根据任何输入创造出任何东西的全新模型。

而且现在Google的视频模型，已经被大家认为唯一一个能勉强跟Seedance 2.0打一打的模型了，也是很多AI漫剧公司最后的希望。

在宣发上，看着效果感觉还行。

目前也已经上线了，但是吧，我体验了一下，只能说，有点拉了。

就真的有一点不太行，而且中文的口音，一股港台腔，真的怪怪的。

emmmm。

别说看起来了，用起来也不如Seedance啊。。。

不过有一个功能值得一提，就是它支持保持视频中某一个片段不变，只修改其他部分。

不过今天发布的是Gemini Omni Flash，拉一点感觉也能理解，毕竟是Omni家族的第一个模型，google也明确说了，Omni Pro即将发布。

## 二. Gemini产品

### 1. Gemini App 全新设计

Gemini App的设计语言，正式名字叫Neural Expressive。

一打开网页端，整体配色，从之前那个灰白色的界面，换成了一个蓝色渐变的背景。

第一眼会觉得挺高级的，但也有点像。。。手机省电模式？

手机端也是。

工具栏做了一个合并，之前上传文件、调用工具、选附件是分散在不同地方的，现在全塞进了一个+号里。

点开模型选择器，底下有一个思维水平的选项，展开以后有标准和扩展两项。

最让我没想到的是设置里，Google也开始整限额了。。。

打开设置一看，好家伙，两个进度条，一个当前使用情况，一个每周限额。

不学Claude好的方面，净学这方面。。。

目前，新设计Neural Expressive今天起在Android、iOS、Web全球上线。

### 2. Ask Maps

Google Maps来了一个十年最大升级，加了个叫Ask Mapx的功能。

你现在，可以直接用自然语言跟地图对话。

现场举了个例子，有家长真的问了这么一个问题："我家孩子刚掉进鸭子池塘，婚礼30分钟后就开始了，我能走着去哪里给她买件新裙子？"

这种问题你以前在搜索框里根本没法打，现在可以了。

Google的生态还是太猛了，把地图这种东西，接到了Gemini里，还是能产生一些化学反应的。

### 3. Ask YouTube

YouTube也搞了一个类似的东西，叫Ask YouTube。

你也不用再自己翻视频了，直接问它"怎么教三岁小孩骑自行车，他已经会骑平衡车了"，它会给你一个整理好的概览、小贴士、最相关的视频片段，甚至直接跳到视频里最对口的那一段。

还能追问，它记得上下文。

跟上面那个功能其实思路是一样的，把搜索框变成对话框，不管是地图还是视频。

Ask YouTube现在在美国对Premium订阅者开放，今年夏天全美推广。

### 4. Docs live

之前你想让Gemini帮你写个文档，得敲一段很精准的prompt，想清楚了再打字。

然后Docs Live的思路是，你不用打字了，直接说话就行。

脑子里想到什么就说什么，说乱了也没关系，Gemini自己整理。

现场他们搞了个演示，一个工程师要给高中母校的职业日做分享，他就对着Gemini一顿说，"把我简历从Drive里调出来""想几个搞笑的类比""哦对把学校发的那封邮件里的时间地点也抓出来""做成表格""在最前面加个备注让我别忘了讲我哥的故事，加粗"。

全程没打一个字，就是一直一边想一边说，说完文档就直接出来了。

非常的丝滑。

最有意思的是中途改主意，比如他说Thursday，然后立刻改口说Friday，Gemini就会自动把Thursday抹掉换成Friday，这个还挺好的。

今年夏天对Pro和Ultra订阅者开放。Gmail Live和Google Keep的Live模式后面也会接入。

### 5. Gemini Live升级

Gemini Live的语音更新。

现场放了几段，利物浦腔的英语、印度哈里亚纳方言、巴西里约葡萄牙语。。。

三个口音切来切去玩了一段。

接下来几周会陆续上线更多。

### 6. Daily Brief

这是Gemini App里一个新功能，每天早上给你一份个性化摘要。

它会自己翻你的邮箱、日历、任务清单，挑出今天最重要的事情，按主题分好类，甚至建议你下一步该做什么，比如提醒你还书、出行时间之类的。

今天起面向美国的Plus、Pro、Ultra用户开放。

### 7. NotebookLM

功能上增加了电影级视频概览，你丢一堆资料进去，它能直接生成一段带流畅动画和视觉效果的讲解视频。

信息图也升级了，现在有10种预设风格可选，手绘风、可爱风、专业风、科学风、动漫风、黏土风。。。

学习工具这块，闪卡和测验都改了，进度会跨设备保存。

最大的变化是，NotebookLM跟Gemini App打通了。Gemini里现在有一个笔记本功能，你在 Gemini里创建的笔记本会自动同步到NotebookLM，反过来也一样。

还支持上传EPUB电子书了，幻灯片可以导出PPTX格式，聊天记录自动保存，可以在对话里直接生成播客、视频、报告。

另外NotebookLM也进了Google Classroom，大学生可以在课堂里直接创建自己的课程笔记本，用老师提供的资料生成学习工具。

## 三. Agent系统

Agent今年是Google整场发布会的真主线。

### 1. Antigravity2.0

先讲Antigravity2.0。

Antigravity是Google的之前的开发平台，但是真的难用，而且完全没啥更新，去年11月才发布的，当时发了之后我们每天干的最多的事，就是把Antigravity的Claude额度给反代出来给OpenCode用，后面开始封号，我基本也就没咋用过了。

今天，终于版本来到了2.0。

更新内容有几个。

第一，全新独立桌面应用。这跟之前是个IDE插件不一样了，是个真正的Agent工作环境了。

第二，Antigravity CLI上线，全球可用。

这其实就是直接把Gemini CLI给替代了。

Google官方公告，2026年6月18日之后，Gemini CLI和Gemini Code Assist IDE扩展会停止对Pro/Ultra用户服务。

开发者要全部迁到Antigravity CLI。

这条信息对所有用Gemini CLI开发的人都注意一下（虽然我估计可能没有），别到6月18号才发现自己的工作流挂了。

第三，Antigravity SDK，开发者可以把Google用在Antigravity里的agent harness，直接拿到自己的服务器上跑。

第四，原生语音支持，整合Gemini音频模型，跟Android、Firebase、AI Studio都打通了。

然后他们现场演示了一下，让Antigravity配合Gemini 3.5 Flash，从零构建一个可运行的操作系统。

93个subagent并行跑，12个小时，1.5万次模型请求，处理26亿token，总成本不到$1000。

还真搞了个OS出来，能跑命令行，能跑doom游戏，可以放动画。

还挺有意思的。

更骚的是3.5 Flash在Antigravity里被专门优化过，跟别的模型相比，不是4倍快，是12倍快了。。。

Antigravity 2.0全球开放，所有人今天都能用。

### 2. Gemini Spark

接下来是Gemini Spark。

你的个人AI Agent，感觉是对标了OpenClaw。

它跑在Google Cloud的专属虚拟机上，24/7不间断，你可以关掉你的电脑，Spark也会在云端继续干活。

由Gemini 3.5 Flash和Antigravity harness驱动，可以处理长链路后台任务。

也直接打通了Google 全家桶，帮你打理各种事。

比如，在工作中让Spark帮团队写一封邮件，汇总最近一周Gemini Live的发布和成绩等等。

Spark会自己去翻你的Docs、邮件、聊天记录，把最重要的信息抓出来，然后按照你预设的写作风格起草邮件。

或者是在生活中，筹备一场街区派对。

Spark在Google Sheets里生成实时RSVP追踪表，自动跟Gmail打通，邻居回复一句"我来"表格就会自动更新，没回复的邻居它自己会生成催回复的邮件草稿。

然后又从Google Drive里翻出了小区HOA的章程，提醒你周五下午之前不能布置充气城堡，还在Google Slides里做了一份派对宣传deck。。。

目前，Spark本周对一些测试人员开放，下周开始对美国Google AI Ultra订阅者开放Beta测试。

注意，是Ultra订阅者，不是Pro，不过说真的，这年头谁家好人会没事给Google冲250刀的Ultra会员啊，过于大冤种了。

所以呢，伴随着Spark发布的，是Google整个订阅价格体系的重新洗牌。

Google AI Ultra之前只有一档，$250一个月，这次拆成两档。

新的$100/月Ultra plan，给开发者、技术lead、内容创作者准备，5倍于Pro的用量、20TB云存储、YouTube Premium、优先用Antigravity。

老的Ultra plan从$250降到$200/月，保留所有顶配能力。

Spark在$100和$200两档都可以用。

按我意思来说，Google你的价格其实还得再降降才行。

### 3. Android Halo

Spark在云端24/7干活，但你怎么看它在干啥呢。

答案是Android Halo。

Halo是Android上一个专门给Agent准备的home base，会在状态栏顶部显示Agent正在干什么。

Spark做什么、做到哪一步、要不要你确认，都在这条状态栏里。

今年晚些时候上线。

Halo其实被带过的比较快，但是我觉得还挺有意思的，可能会是一个新的UI层级。

过去的Android UI都是给App用的，App是底层逻辑。

Halo开始的Android，是给Agent用的，Agent是底层逻辑。

可能未来会诞生很多新的玩法。

## 四. 视觉生成

### 1. Google Pics

Workspace里的新产品，Google Pics。

注意是Pics，不是Pix，跟Google Photos区分开。

Pics是图像创作和编辑工具，做派对传单、信息图、活动海报这种东西。

支持目标分割，可以选中图里任何一个元素单独编辑。

比如把一只狗变成一只猫，或者把毛衣换个颜色，背景可以完全不动。

文字也能直接在图里编辑、一键翻译多语种啥的。

所有输出自动加SynthID水印，保证可以被溯源。

今年夏天先在美国上Ultra订阅者。

### 2. Stitch

Stitch是Google做UI设计的工具。

过去一年，全球用户用Stitch生成了超过1亿张UI画面，Google说内部自己也在用。

（PS：用过这个的可以举个手）

这次更新有几个，实时语音协作（你说话、UI实时改），导出代码、直接发布到Netlify、跟Antigravity打通。

Google有段披萨店的演示还挺好玩的。

两个完全不懂UI设计的人，对着Stitch一通说，"menu突出更多披萨选项"， "header字大一点"啥的。

UI实时响应，最后一键发布上线。

### 3. Google Flow

老朋友了，Flow就是Google的AI creative studio。

这次更新有四个。

1.加入Gemini Omni，可以保留原始视频里的表演和动作，只改环境和特效。

2.新Agent功能。一张图同时生成16段不同机位的视频，比如你给它一张街景，它给你出16种镜头语言的视频。

3.大规模场景修改。把所有镜头从清晨变成深夜，灯光、阴影、车灯，整个场景自洽切换。

4.Flow Tools。你可以在Flow里vibe code自己的创意工具，比如做视频特效、手绘动画、文字图层叠加啥的。

最好玩的是Flow Music。

现场演示了一段。一个团队成员录了一段钢琴riff，扔进Flow Music，跟它说"往R&B方向走，加女声"。然后它就给出了一段编曲完整的歌。

效果还可以的，比Suno还差点，但是作为小demo其实够用了。

所以其实在这里，Flow的发布逻辑就很清晰了。

想做做创意人的整个工作流入口。

从画板、到剧本、到镜头、到剪辑、到调色、到配乐，一站式想全包。

但是坦率的讲，功能确实全，但是也真的不咋好用。。。

### 4. SynthID

还有一个小更新，SynthID。

Google做的AI水印技术，专门用来标记哪些内容是AI生成的。

已经给超过1000亿张图片和视频打了水印，还有累计6万年时长的音频。

新的变化是，现在你在Chrome里右键点一张图，或者用圈选搜索，就能查这张图是不是AI生成的。

还玩了个梗，说去年有一张他吃汉堡的图在社交媒体传疯了，但其实是假的，他原话说"I don't eat hamburgers"。

最让我意外的是，Google宣布OpenAI、Kakao、ElevenLabs也加入了SynthID。

OpenAI也发了公告。

这是这次发布会最有故事感的一个细节。

过去三年这两家恨不得搞死对方，今天他们在SynthID这件事上放下芥蒂一起合作了。

AI生成的假图、假声音、假视频这个问题，已经严重到大家不得不放下架子一起搞了。

Nvidia去年加入，Sony Pictures、Reuters、TikTok也在路上。

## 五. Google搜索

AI Mode月活已经突破 10 亿，自上线以来每个季度查询量翻一倍。

然后今天也官宣底层模型升级成了Gemini 3.5。

具体的更新有四个。

### 1. 重做了搜索框

Google说这是搜索框25年以来最大的一次升级。

以前你只能打字，现在可以丢图片、文件、视频进去，搜索会跨模态一起理解。而且它会用AI帮你补全问题，帮你把真正想问的问题梳理出来。

### 2. AI Overviews和AI Mode合并了

从搜索结果页自然过渡到对话式追问，上下文可以一直跟着你。

### 3. Search Agents

搜索里可以创建Agent了。可以在搜索里同时启动多个Agent，让它们7x24小时在后台帮你盯着事情。

比如说，你是炒股的，想盯PE小于15、现金流为正、负债低的生物科技股，AI agent接到指令自己去查，看到价格变动给你推送更新，可以放你方便的把信号和噪音分开等等。

### 4. Agentic Coding 进了搜索

搜索现在会针对你的问题，实时从零搭建定制化的交互界面。

比如问黑洞怎么影响时空的，可以直接生成了一个可以拖拽参数的交互式的可视化页面。

这玩意背后是Antigravity在驱动。

搜索的时候调用了一个containerized agent环境，让3.5 Flash实时写代码、跑代码、把渲染结果嵌回搜索结果。

这玩意今年夏天对所有用户免费开放。

直接在搜索里面嵌入生成式UI，可能是搜索这个产品形态自1998年以来最大的一次进化。

## 六. Agent电商

这块整个是新增的板块，但是反而是今天发布会最有意思的板块。

两个支柱协议加一个新产品，凑成了完整的三件套。

### 1. Universal Commerce Protocol（UCP）

UCP是Google一月份发布的开源协议，定位是Agent电商时代的HTTP。

你可以简单的理解成，给Agent自己去买东西时候用的一套通用购物规则，类似MCP。

Google在NRF零售展会上提出来的时候，已经拉了Shopify、Etsy、Wayfair、Target、Walmart五家创始合作伙伴一起搞了，还找到一群公司来背书。

这次I/O的新进展是，Amazon、Meta、Microsoft、Salesforce、Stripe官宣加入了UCP的技术委员会。

Vidya原话是："it may very well be the first time we've all agreed on something"，这可能是我们所有人第一次达成共识。

之前只在美国上，现在开始扩展到加拿大、澳大利亚，英国也紧随其后。

### 2. Agent Payments Protocol（AP2）

AP2你可以简单的理解成，给 Agent付款用的授权协议。

AP2解决的的，其实就是Agent帮你买东西会不会乱花钱的问题。

你可以给Agent设三道护栏。具体品牌、具体商品、支付金额上限，三个条件全满足，Agent才会下单。

每一笔交易都有tamper-proof digital mandate，也就是篡改防护的数字授权书，如果有问题，你和商家看到的是同一份记录，可以追溯。

AP2即将先在Gemini Spark上线。

### 3. Universal Cart

这是这次I/O真正的新发布。

一个跨商家、跨服务的智能购物车。

你在Search里看到一个东西可以加进去，跟Gemini聊天看到一个东西可以加进去，看YouTube视频时看到一个东西可以加进去，连读Gmail时看到一个东西也可以加进去。

加进去之后这个购物车自动在后台干活，找折扣、查价格历史、对你账户里的支付卡权益、提醒缺货补货、跨商品检查兼容性。

比如说，你买电脑配件，先加了一块主板进购物车，之前你已经买过一个CPU。Universal Cart发现你CPU和主板不匹配，主动给你提醒，让你换个主板。

这种能力是Google搜索过去20年从来没有的能力。

我自己是真的有点期待了，非常的有意思。

Universal Cart今年夏天美国上线，先在Search和Gemini App里，YouTube和Gmail后面跟进。

Agent+钱这块的基础设施，已经开始缓缓渐进了。

## 七. 其他

### 1. Android XR智能眼镜

Android XR眼镜会有两条路线。

一类是带镜片显示屏的显示眼镜，去年I/O已经展示过，今年晚些时候会扩大测试计划。

另一类是今年秋天要发的的首款音频眼镜。

没有镜片显示屏，靠声音跟你交互，平时听音乐、拍照、打电话、调App。

Gentle Monster和Warby Parker负责的外观设计，三星做的硬件，同时支持IOS和Android。

现场演示挺有意思的。

一个姑娘戴着眼镜，跟Gemini说带我去上周跟朋友见面的那个地方，Gemini直接设好了导航，还主动问要不要顺路买你常喝的那杯冷萃咖啡？然后自己打开手机上的外卖App帮她下了单。

最后拿眼镜给观众拍了张合影，让Gemini把照片变成卡通风格，还加了个大飞艇，放在手表上看。

### 2. TPU

TPU 这次也有一次比较大的更新。

第八代TPU，是Google历史上第一次采用了双芯片路线，分别针对训练和推理做优化。

训练芯片叫TPU 8t，主要面向大规模预训练。原始算力接近上一代的3倍。

提到一套叫Jackson Pathways的训练基础设施，可以把训练任务分布到多个数据中心，不再受单个超大数据中心限制，最高能跨全球超过100万颗TPU做scaling。

推理芯片叫TPU 8i，重点是降低延迟、提升生成速度。

Google现场用一个即将发布的Flash模型做演示，让它生成一个Chrome Dino小游戏，屏幕上显示的生成速度接近每秒1500个token。

速度确实快的有点过于离谱了。

### 3. AI科研

发布会最后，Google讲了AI在科学领域的几个项目。

一个是Gemini for Science，新发布的科研工具集，包含三个实验性原型。

第一个叫假设生成器，基于Co-Scientist底层系统，让多个agent一起生成、辩论、评估科研假设，每个论点都有可点击的引用来源。

第二个叫计算发现引擎，基于AlphaEvolve和ERA，并行生成上千个代码变体，让科学家几小时跑完原本要几个月的实验。

第三个叫科学技能包，针对生物医药，整合了UniProt、AlphaFold Database、AlphaGenome API、InterPro等30多个生命科学数据库，复杂分析从几小时压到几分钟。

除了Gemini for Science之外，还有两个东西。

一个叫Weather Next。AI天气预报，比传统模型更准、更早预警。

去年的梅丽莎飓风袭击牙买加，Weather Next提前3天预测到了，比传统模型更准确，帮助当地提前撤离居民，救了不少人。

一个是AI制药。Google旗下Isomorphic Labs用AI加速新药研发，已经有多个项目进入临床前阶段，针对免疫疾病和癌症。Hassabis说目标是"one day solving all disease"，有朝一日治好所有的病。

除了几个科研的之外，还有一个Code Mender。能自动找到代码里的安全漏洞并修好，今天起对一小批专家开放Code Mender API测试。

程序员看到这块应该挺安心的。

毕竟Agent写的代码越来越多，安全漏洞自动修复这件事，已经是基础设施级别的需求了。

## 写在最后

终于。。。总结完了。。。

Google每次的发布会是真的信息量大到让人窒息。

最后，Hassabis结束的时候。

他说了一句让我还蛮动容的话。

他说：

> When we look back at this time, I think we'll realize that we were standing in the foothills of the singularity
>
> 当我们回望这个时刻时，我想我们会意识到，我们正站在奇点的山脚下。

我也确实相信这句话。

AI，至少在现在看，它是人类智慧的放大器。

也许，我们会开启一个，科学发现和进步的新黄金时代。

也希望未来。

我们能不断的，一起见证。

以上，既然看到这里了，如果觉得不错，随手点个赞、在看、转发三连吧，如果想第一时间收到推送，也可以给我个星标⭐～谢谢你看我的文章，我们，下次再见。
