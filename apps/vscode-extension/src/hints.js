// Teaching scaffolds surround the original, licensed question hints; no answer generation.
function hintSteps(lesson) {
  const programming = ['programming', 'debugging'].includes(lesson.questionType);
  const original = (lesson.hints || []).filter((hint) => typeof hint === 'string' && hint.trim());
  return [
    { title: '第 1 层 · 理清需求', text: programming
      ? '先用一句话描述函数应该完成什么，列出输入、输出；手算一个普通例子，再开始写代码。'
      : '先不要猜答案：圈出题目中的关键条件，用自己的话解释它；有代码时逐行记录变量的变化。' },
    ...original.map((text, i) => ({ title: `第 ${i + 2} 层 · ${i === 0 ? '题目关键线索' : '进一步提示'}`, text })),
    { title: `第 ${original.length + 2} 层 · 自查与验证`, text: programming
      ? '对照函数声明检查参数与返回值，再检查循环边界、变量初始化和指针目标。选择空输入、边界值或重复值中适用的情况，说明预期结果；不要只以一个例子通过作为结束。'
      : '尝试改变题目中的一个条件，看原结论是否仍然成立。提交后结合解析，解释为什么其他选项或另一种判断不成立。' }
  ];
}
module.exports = { hintSteps };
