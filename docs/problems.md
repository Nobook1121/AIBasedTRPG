# 已确认问题
1. 别的玩家在发送消息后，我方这边显示的“AI正在思考”下方的已耗时计时错误
2. 查询最近的两次日志，发现在ai的回复内容有如下内容：“用户明确表达了要前往5号车厢的行动意图。根据系统规则，当玩家明确进入、离开或转换场景时，我应该调用 `room.activate_scenario_scene`。虽然之前调用失败了（可能是因为系统需要更明确的转换确认），但用户的行动描述非常清晰：\"和咪咕一起跑到五号车厢\"。\n\n让我再次尝试激活场景3（5号车厢），然后读取该场景的详细内容来描述环境。",”应该是正确的思考，但是发现ai在思考完这个之后直接没有后文了，并且也没有在聊天框返回消息
3. 发现在ai思考的时候刷新网页会导致ai思考失败
4. 在log文件中发现这个日志，可能是报错？，请分析解释，如果是错误就修复\"scene transition requires an explicit player transition\
5. ai在多个回合的思考后会导致被打断导致ai不回复内容
6. 每次开启时候ai像开盲盒一样一会聪明一会笨的，请规范kp的回复格式，并且现在发现ai在回复时候的提示过多，请在设置中增加一个开关，控制aikp是否会回复提示。
7. 查看最近log，发现ai又开始篡改剧情，乘务员没有钥匙，但是在ai的描述中直接说有钥匙并且给了我们。请修复。
8.  AI API response payload: {"choices": [{"message": {"content": "", "reasoning_content": "用户决定前往2号车厢。根据剧本模块内容：\n1. 2号车厢内有Clicker怪物\n2. 看到Clicker会造成SAN 1/1d6损失（已检定）\n3. 需要潜行通过或者制造声响引开Clicker\n4. 触发器1需要侦察检定成功后才能触发\n\n现在两位玩家的侦察检定都成功了，可以触发触发器1。\n\n让我先描述场景，然后触发触发器。", "role": "assistant", "tool_calls": [{"function": {"arguments": "{\"trigger_id\": 1, \"condition_met\": true, \"check_name\": \"侦察\"}", "name": "trigger.reveal_scenario_trigger"}, "id": "call_ea47d6a6a65d40929d18c623", "index": 0, "type": "function"}]}, "finish_reason": "tool_calls", "index": 0, "logprobs": null}], "object": "chat.completion", "usage": {"prompt_tokens": 9265, "completion_tokens": 158, "total_tokens": 9423, "completion_tokens_details": {"reasoning_tokens": 97, "text_tokens": 158}, "prompt_tokens_details": {"text_tokens": 9265}}, "created": 1788707687, "system_fingerprint": null, "model": "qwen3.5-plus", "id": "chatcmpl-07a5ac27-b235-9f1b-b906-8670207385d3"}
AI API response payload: {"choices": [{"message": {"content": "", "reasoning_content": "无书的侦察检定成功了（65/85），现在可以触发触发器1了。", "role": "assistant", "tool_calls": [{"function": {"arguments": "{\"trigger_id\": 1, \"condition_met\": true, \"check_name\": \"侦察\"}", "name": "trigger.reveal_scenario_trigger"}, "id": "call_8f3b2c635b2042f482bb5ab2", "index": 0, "type": "function"}]}, "finish_reason": "tool_calls", "index": 0, "logprobs": null}], "object": "chat.completion", "usage": {"prompt_tokens": 9772, "completion_tokens": 81, "total_tokens": 9853, "completion_tokens_details": {"reasoning_tokens": 20, "text_tokens": 81}, "prompt_tokens_details": {"text_tokens": 9772}}, "created": 1788707847, "system_fingerprint": null, "model": "qwen3.5-plus", "id": "chatcmpl-0050c719-de80-9f3a-9197-61db8bd393a6"} 
这些是两段ai的对话记录发现ai在调用触发器后直接触发失败，并且什么回复都没有，日志里面也什么都不显示，请修复（补充信息：触发器1是一个需要发送图片的触发器，可能和这个有关）
9. ai检定有时候会不调用骰娘，或者没有通过骰娘发出判定结果
10. san减少没有在角色卡上做出反应
11. 可以尝试如果玩家在某些场景做出了一些比较重要的决定（如最近的一个log中的剧本，带上了乘务员，可以进行一个记忆）
12. 触发器在抛出文件时候可能有问题，并且在剧本编辑和预览中的含有文件的触发器没有文件预览。


**请分步解决以上这些问题，并且确保问题被解决，允许激进修改，但是不要让代码坏掉或者偏离原本的功能**