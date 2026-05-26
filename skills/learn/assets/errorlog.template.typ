#set page(paper: "a4", margin: 1.8cm)
#set text(font: ("PingFang SC", "Arial Unicode MS"), size: 10.5pt, lang: "zh")
#set par(justify: true, leading: 0.62em)

= {TOPIC} 错题与误区日志

用途：记录学习过程中暴露出的错误、模糊理解、概念混淆、迁移失败和关键盲点。这个文件决定后续复习顺序。

记录规则：

- 只记录会影响后续理解或应用的错误，不记录每个小瑕疵。
- 保留学习者原始回答的意思，避免事后美化。
- 每条错误必须包含正确理解和下一次复习动作。
- 连续两次跨会话答对，才可以从 `review` 改为 `closed`。

== 错误分类

#table(
  columns: (3.0cm, 1fr),
  inset: 5pt,
  align: left,
  [类型], [说明],
  [concept], [概念混淆。],
  [source], [没有说清楚依据来自哪份资料，或脱离资料泛泛而谈。],
  [application], [不能迁移到新场景。],
  [boundary], [忽略边界条件或失败模式。],
  [terminology], [术语不熟。],
  [method], [解题方法、分析步骤或学习策略错误。],
  [process], [学习流程问题，例如跳过提问或复盘。],
)

== 活跃错误表

#table(
  columns: (1.1cm, 1.6cm, 1.7cm, 2.3cm, 1fr, 1fr, 2.0cm, 1.5cm),
  inset: 3.6pt,
  align: left,
  [ID], [日期], [课程], [类型], [错误表现], [修正解释], [复习日期], [状态],
  [E000], [{DATE}], [Plan], [process], [尚未开始正式问答。], [从 L001 开始，用验证问题暴露真实薄弱点。], [{DATE}], [open],
)

== 新错误记录模板

#table(
  columns: (3.0cm, 1fr),
  inset: 5pt,
  align: left,
  [字段], [内容],
  [ID], [E001],
  [日期], [YYYY-MM-DD],
  [课程], [L???],
  [类型], [concept / source / application / boundary / terminology / method / process],
  [原问题], [助教提出的验证问题。],
  [学习者回答], [保留学习者原意，避免事后美化。],
  [错误表现], [具体指出错在哪里。],
  [正确理解], [用简单语言修正。],
  [为什么重要], [如果这个错误保留下来，会影响哪类理解、题目、项目或判断。],
  [复习动作], [下一次如何验证是否真正掌握。],
  [复习日期], [YYYY-MM-DD],
  [状态], [open / review / closed],
)
