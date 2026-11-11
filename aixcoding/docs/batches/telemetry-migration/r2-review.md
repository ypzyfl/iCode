# 0.35.2 企业埋点迁移 R2 逐行审阅稿

基线为 `10ec90eefc75274ba9b1acd8c25f4a39964234b1`。本文是 design.md §7 的签认附件。下面的差异由该提交上的上游文件生成，逐块对应签认范围。定制包 API 和端到端行为由签认后的实施验证覆盖。

源码共 17 个文件，**+179/−19**。另有一个由上游工具生成的 wait manifest。

| 上游文件 | 新增 | 删除 |
| --- | ---: | ---: |
| `src/chrys/app/acp/server.py` | 19 | 4 |
| `src/chrys/foundation/events/types.py` | 7 | 0 |
| `src/chrys/kernel/loop.py` | 7 | 0 |
| `src/chrys/kernel/middleware.py` | 2 | 0 |
| `src/chrys/orchestration/engine/build/builder.py` | 9 | 1 |
| `src/chrys/orchestration/engine/engine.py` | 14 | 0 |
| `src/chrys/orchestration/engine/run/active_injection.py` | 7 | 0 |
| `src/chrys/orchestration/engine/run/bindings.py` | 2 | 0 |
| `src/chrys/orchestration/engine/run/runner.py` | 7 | 0 |
| `src/chrys/orchestration/invoker/kernel.py` | 11 | 0 |
| `src/chrys/orchestration/sub_agents/tools.py` | 9 | 1 |
| `src/chrys/orchestration/workflows/agent_node_build.py` | 9 | 1 |
| `src/chrys/service/agent_middleware/events/hosted_tools.py` | 10 | 1 |
| `src/chrys/service/agent_middleware/events/sub_agent_events.py` | 12 | 0 |
| `src/chrys/service/agent_middleware/events/tool_events.py` | 10 | 0 |
| `src/chrys/service/agent_middleware/response_validation.py` | 34 | 10 |
| `src/chrys/service/llm/clients.py` | 10 | 1 |
| `tests/architecture/trajectory_wait_manifest.json` | 19 | 14 |

## 每组变更的归属

每组改动在 diff 中以 R3 标记定位。声明、实参和字段归其接口所在层。try、lazy import、调用和异常分支留在接线处，由定制包负责业务函数体。wait manifest 由标准工具更新。

| 文件 | R3 标记中的动作 | 上游锚点 | 归属理由 | 验收 |
| --- | --- | --- | --- | --- |
| `src/chrys/orchestration/engine/engine.py` | attach bus | `AgentEngine._subscribe_event_handlers` | 由引擎持有 bus 并确定注册时点。定制包负责订阅、幂等及异常记录。 | T07 |
| `src/chrys/orchestration/engine/engine.py` | detach bus | `AgentEngine._release_resources` | 引擎释放任务提供正常排空时点。定制包负责有界关闭和清理。 | T07 |
| `src/chrys/orchestration/invoker/kernel.py` | bind pass | `KernelConversation.run` | 显式提交本次 RunRequest 与 pass 标识，定制包保存并隔离作用域。 | T06 |
| `src/chrys/orchestration/invoker/kernel.py` | reset pass | `KernelConversation.run finally` | 引擎拥有 pass 的 finally，定制包提供幂等且自行降级的恢复回调。 | T06 |
| `src/chrys/service/llm/clients.py` | assemble model middleware | `_assemble_stack before ToolLoopLayer` | 统一组栈负责装配。报文、配置、GET 语义和发送失败处理归定制 middleware。 | T01 |
| `src/chrys/service/llm/clients.py` | install model middleware | `_assemble_stack ToolLoopLayer` | 将可选 middleware 装入真实客户端，禁用或装配失败时使用原空链。 | T01 |
| `src/chrys/orchestration/engine/build/builder.py` | build agent context | `build_agent create_client` | 当前构建方提供实际 Agent 和工作区。定制包仅包装此次工厂调用，保留原工厂实参和回退。 | T01,T05,T06 |
| `src/chrys/orchestration/sub_agents/tools.py` | build agent context | `sub-agent create_client` | 当前构建方提供实际 Agent 和工作区。定制包仅包装此次工厂调用，保留原工厂实参和回退。 | T01,T05,T06 |
| `src/chrys/orchestration/workflows/agent_node_build.py` | build agent context | `build_kernel_node create_client` | 当前构建方提供实际 Agent 和工作区。定制包仅包装此次工厂调用，保留原工厂实参和回退。 | T01,T05,T06 |
| `src/chrys/kernel/middleware.py` | chat call source | `ChatContext.__init__` | ChatContext 保存单次调用内部身份，生命周期和外发字段由定制 middleware 决定。 | T06 |
| `src/chrys/kernel/loop.py` | bind tool source | `_stamp_function_call_operations` | 此处同时持有原 Content 与 kernel 刚生成的操作 ID，定制包按对象身份绑定来源。 | T06 |
| `src/chrys/foundation/events/types.py` | declare tool start | `InvocationToolCallStart` | 事件类型声明携带已有事实。默认值兼容其他发布者，企业模块负责报文编码。 | T06 |
| `src/chrys/foundation/events/types.py` | declare tool result | `InvocationToolCallResult` | 事件类型声明携带已有事实。默认值兼容其他发布者，企业模块负责报文编码。 | T06 |
| `src/chrys/service/agent_middleware/events/tool_events.py` | capture tool operation | `_process_tool_call before approval` | 执行前捕获稳定工具 ID，开始和结果复用，业务关联归定制包。 | T06 |
| `src/chrys/service/agent_middleware/events/tool_events.py` | publish local start | `_process_tool_call InvocationToolCallStart` | 发布已有 provider、操作和工作区事实，旧 funcId 与报文项目字段归定制包。 | T02,T03,T05,T06 |
| `src/chrys/service/agent_middleware/events/tool_events.py` | publish local result | `_process_tool_call InvocationToolCallResult` | 将终态与执行前的操作身份配对，复用已有结果快照。 | T02,T03,T06 |
| `src/chrys/service/agent_middleware/events/sub_agent_events.py` | capture tool operation | `_process_tool_call before approval` | 执行前捕获稳定工具 ID，开始和结果复用，业务关联归定制包。 | T06 |
| `src/chrys/service/agent_middleware/events/sub_agent_events.py` | publish local start | `_process_tool_call InvocationToolCallStart` | 发布已有 provider、操作和工作区事实，旧 funcId 与报文项目字段归定制包。 | T02,T03,T05,T06 |
| `src/chrys/service/agent_middleware/events/sub_agent_events.py` | publish local result | `_process_tool_call InvocationToolCallResult` | 将终态与执行前的操作身份配对，复用已有结果快照。 | T02,T03,T06 |
| `src/chrys/service/agent_middleware/response_validation.py` | failed observation source | `ResponseValidationMiddleware._observe_failed_response` | 失败响应携带真实来源，错误分类仍由上游负责。 | T06 |
| `src/chrys/service/agent_middleware/response_validation.py` | forward failure source | `ResponseValidationMiddleware._observe_failed_response` | 将失败请求来源传给既有观察出口。 | T06 |
| `src/chrys/service/agent_middleware/response_validation.py` | observation source parameter | `ResponseValidationMiddleware._notify_contents_observed` | 模型来源作为观察调用的可选事实，保持原观察者接口。 | T06 |
| `src/chrys/service/agent_middleware/response_validation.py` | remember hosted source | `ResponseValidationMiddleware._notify_contents_observed` | 观察出口同时持有真实内容与请求来源，定制包只在内存登记对象身份。 | T06 |
| `src/chrys/service/agent_middleware/response_validation.py` | bind blocking failure | `ResponseValidationMiddleware.process` | 从实际调用上下文传递失败来源。 | T06 |
| `src/chrys/service/agent_middleware/response_validation.py` | bind stream failure | `ResponseValidationMiddleware.process` | 从实际调用上下文传递失败来源。 | T06 |
| `src/chrys/service/agent_middleware/response_validation.py` | capture stream source | `ResponseValidationMiddleware.process` | 流回调在请求调用退出后运行，闭包固定实际调用上下文。 | T06 |
| `src/chrys/service/agent_middleware/response_validation.py` | stream source parameter | `ResponseValidationMiddleware._observe_update` | 流观察接收实际调用来源。 | T06 |
| `src/chrys/service/agent_middleware/response_validation.py` | forward stream source | `ResponseValidationMiddleware._observe_update` | 在流内容发布前关联来源。 | T06 |
| `src/chrys/service/agent_middleware/response_validation.py` | forward terminal source | `ResponseValidationMiddleware._conclude` | 终态 Content 可以重建，观察时用同次调用重新关联。 | T06 |
| `src/chrys/service/agent_middleware/events/hosted_tools.py` | hosted view source | `HostedToolView` | 可选来源随展示操作缓冲和发布，独立于展示元数据。 | T06 |
| `src/chrys/service/agent_middleware/events/hosted_tools.py` | adapt hosted source | `adapt_hosted_tool` | 此处持有实际 call/result Content。按对象取来源，缓冲和重建均可携带。 | T06 |
| `src/chrys/orchestration/engine/run/bindings.py` | publish hosted source | `_publish_hosted_operation HostedToolStartOp` | Start 携带模型来源，Result 沿用既有展示 occurrence 配对，报文关联归定制订阅器。 | T06 |
| `src/chrys/service/agent_middleware/events/sub_agent_events.py` | publish hosted source | `_publish_hosted_operation HostedToolStartOp` | Start 携带模型来源，Result 沿用既有展示 occurrence 配对，报文关联归定制订阅器。 | T06 |
| `src/chrys/orchestration/engine/run/runner.py` | record input skill | `_skill_reference_reminder matched branch` | 沿用旧版普通输入或追加输入命中时点，定制包读取会话字段并发送 saveOnly。 | T04 |
| `src/chrys/orchestration/engine/run/active_injection.py` | record input skill | `_skill_reference_reminder matched branch` | 沿用旧版普通输入或追加输入命中时点，定制包读取会话字段并发送 saveOnly。 | T04 |
| `src/chrys/app/acp/server.py` | prepare desktop scope | `ChrysAcpServer.prompt` | ACP 边界接收实际 metadata，解析、验证和异常降级归定制包。 | T04 |
| `src/chrys/app/acp/server.py` | bind desktop scope | `ChrysAcpServer.prompt run` | 覆盖现有 turn 运行与子任务，退出时解除绑定。 | T04 |
| `src/chrys/app/acp/server.py` | merge normal response | `ChrysAcpServer.prompt end_turn` | 在既有新版 metadata 构造点合并旧 envelope，定制包编码旧字段。 | T04 |
| `src/chrys/app/acp/server.py` | merge cancelled response | `ChrysAcpServer.prompt cancelled` | 在既有新版 metadata 构造点合并旧 envelope，定制包编码旧字段。 | T04 |

## 逐行差异

### `src/chrys/app/acp/server.py`

```diff
--- a/src/chrys/app/acp/server.py
+++ b/src/chrys/app/acp/server.py
@@ -563,7 +563,14 @@
         **kwargs: Any,
     ) -> acp_schema.PromptResponse:
         """Run one ACP prompt turn."""
-        _ = kwargs
+        # AIxCoding telemetry: prepare desktop scope (src/chrys/app/aixcoding/telemetry)
+        desktop_scope = None
+        try:
+            from chrys.app.aixcoding.telemetry.acp import prompt_scope
+
+            desktop_scope = prompt_scope(session_id, kwargs)
+        except Exception:
+            pass
         if self._client is None:
             raise internal_error({"details": "ACP client connection is not ready."})
         user_message_id = _validated_message_id(message_id)
@@ -593,13 +600,18 @@
             async for event in session.host.iter_turn_events(message):
                 yield event
 
-        turn = await self._run_turn(session_id, start)
+        # AIxCoding telemetry: bind desktop scope (src/chrys/app/aixcoding/telemetry)
+        with desktop_scope if desktop_scope is not None else contextlib.nullcontext() as desktop:
+            turn = await self._run_turn(session_id, start)
         if isinstance(turn.outcome, EndTurn):
             return acp_schema.PromptResponse(
                 stopReason="end_turn",
                 userMessageId=user_message_id,
                 usage=acp_schema.Usage.model_validate(turn.turn_usage),
-                field_meta=with_chrys_metadata(None, turn.response_meta()),
+                # AIxCoding telemetry: merge normal response (src/chrys/app/aixcoding/telemetry)
+                field_meta=with_chrys_metadata(
+                    desktop.response_meta() if desktop is not None else None, turn.response_meta()
+                ),
             )
         if isinstance(turn.outcome, Refused):
             return acp_schema.PromptResponse(
@@ -613,7 +625,10 @@
                 stopReason="cancelled",
                 userMessageId=user_message_id,
                 usage=acp_schema.Usage.model_validate(turn.turn_usage),
-                field_meta=with_chrys_metadata(None, turn.response_meta()),
+                # AIxCoding telemetry: merge cancelled response (src/chrys/app/aixcoding/telemetry)
+                field_meta=with_chrys_metadata(
+                    desktop.response_meta() if desktop is not None else None, turn.response_meta()
+                ),
             )
         if isinstance(turn.outcome, Errored):
             raise _turn_failed(turn, turn.outcome.error)
```

### `src/chrys/foundation/events/types.py`

```diff
--- a/src/chrys/foundation/events/types.py
+++ b/src/chrys/foundation/events/types.py
@@ -660,7 +660,12 @@
     provider: str = ""
     provider_item_type: str = ""
     provider_call_id: str = ""
+    # AIxCoding telemetry: declare tool start (src/chrys/service/aixcoding/telemetry)
     provider_status: str = ""
+    tool_operation_id: str | None = None
+    model_source_id: str | None = None
+    agent_profile_name: str = ""
+    workspace_cwd: str = ""
 
 
 @dataclass
@@ -730,7 +735,9 @@
     provider: str = ""
     provider_item_type: str = ""
     provider_call_id: str = ""
+    # AIxCoding telemetry: declare tool result (src/chrys/service/aixcoding/telemetry)
     provider_status: str = ""
+    tool_operation_id: str | None = None
 
 
 @dataclass
```

### `src/chrys/kernel/loop.py`

```diff
--- a/src/chrys/kernel/loop.py
+++ b/src/chrys/kernel/loop.py
@@ -528,6 +528,13 @@
     for function_call in function_calls:
         operation_id = new_analytics_id()
         function_call.additional_properties[OPERATION_ID_KEY] = operation_id
+        # AIxCoding telemetry: bind tool source (src/chrys/kernel/aixcoding/telemetry)
+        try:
+            from .aixcoding.telemetry.provenance import bind_tool_operation_source
+
+            bind_tool_operation_source(function_call, operation_id)
+        except Exception:
+            pass
         operation_by_identity[id(function_call)] = operation_id
         if function_call.call_id:
             operation_by_call_id[function_call.call_id] = operation_id
```

### `src/chrys/kernel/middleware.py`

```diff
--- a/src/chrys/kernel/middleware.py
+++ b/src/chrys/kernel/middleware.py
@@ -223,6 +223,8 @@
         self.function_invocation_kwargs: dict[str, Any] = (
             dict(function_invocation_kwargs) if function_invocation_kwargs is not None else {}
         )
+        # AIxCoding telemetry: chat call source (src/chrys/kernel/aixcoding/telemetry)
+        self.model_source_id: str | None = None
         self.stream_transform_hooks = list(stream_transform_hooks or [])
         self.stream_result_hooks = list(stream_result_hooks or [])
         self.stream_cleanup_hooks = list(stream_cleanup_hooks or [])
```

### `src/chrys/orchestration/engine/build/builder.py`

```diff
--- a/src/chrys/orchestration/engine/build/builder.py
+++ b/src/chrys/orchestration/engine/build/builder.py
@@ -480,7 +480,15 @@
         # only used by opt-in raw HTTP logging; normal transport construction stays
         # unchanged.
         invocation_publishers = InvocationPublishers(bus)
-        client = await create_client(
+        # AIxCoding telemetry: build agent context (src/chrys/service/aixcoding/telemetry)
+        client_factory = create_client
+        try:
+            from chrys.service.aixcoding.telemetry.model import for_agent_build
+
+            client_factory = for_agent_build(create_client, profile.name, runtime.cwd)
+        except Exception:
+            pass
+        client = await client_factory(
             active_profile,
             on_intermediate_text=on_intermediate,
             session_id=session_id,
```

### `src/chrys/orchestration/engine/engine.py`

```diff
--- a/src/chrys/orchestration/engine/engine.py
+++ b/src/chrys/orchestration/engine/engine.py
@@ -551,6 +551,13 @@
         await self._bus.subscribe(InvocationResumed, self._on_sub_agent_unpaused)
         await self._bus.subscribe(InvocationAborted, self._on_sub_agent_unpaused)
         await self._bus.subscribe(InvocationCascadeAborted, self._on_sub_agent_unpaused)
+        # AIxCoding telemetry: attach bus (src/chrys/orchestration/aixcoding/telemetry)
+        try:
+            from chrys.orchestration.aixcoding.telemetry.lifecycle import attach
+
+            await attach(self._bus)
+        except Exception:
+            pass
         await self._workflows.subscribe()
         await self._side_questions.subscribe()
         if self._hook_confirmations is not None:
@@ -597,6 +604,13 @@
             finally:
                 await self._lifecycle.shutdown()
         finally:
+            # AIxCoding telemetry: detach bus (src/chrys/orchestration/aixcoding/telemetry)
+            try:
+                from chrys.orchestration.aixcoding.telemetry.lifecycle import detach
+
+                await detach(self._bus)
+            except Exception:
+                pass
             if self._hook_confirmations is not None:
                 # After the release: what still waits on a question ends unavailable, and no answer is taken after.
                 await self._hook_confirmations.close()
```

### `src/chrys/orchestration/engine/run/active_injection.py`

```diff
--- a/src/chrys/orchestration/engine/run/active_injection.py
+++ b/src/chrys/orchestration/engine/run/active_injection.py
@@ -518,4 +518,11 @@
         reference = parse_skill_reference(text, skill_details or self._current.manifest.runtime_details.skill_details)
         if reference is None:
             return None
+        # AIxCoding telemetry: record input skill (src/chrys/orchestration/aixcoding/telemetry)
+        try:
+            from chrys.orchestration.aixcoding.telemetry.skills import record_skill_reference
+
+            record_skill_reference(reference.skill.name, self._session)
+        except Exception:
+            pass
         return format_skill_reference_reminder(reference)
```

### `src/chrys/orchestration/engine/run/bindings.py`

```diff
--- a/src/chrys/orchestration/engine/run/bindings.py
+++ b/src/chrys/orchestration/engine/run/bindings.py
@@ -444,7 +444,9 @@
                     provider=view.provider,
                     provider_item_type=view.provider_item_type,
                     provider_call_id=view.provider_call_id,
+                    # AIxCoding telemetry: publish hosted source (src/chrys/service/aixcoding/telemetry)
                     provider_status=view.provider_status,
+                    model_source_id=view.model_source_id,
                     tool_kind=HOSTED_TOOL_DEFAULT_KIND_BY_FAMILY.get(view.family, ""),
                     args=view.arguments,
                     session_id=self._session_id,
```

### `src/chrys/orchestration/engine/run/runner.py`

```diff
--- a/src/chrys/orchestration/engine/run/runner.py
+++ b/src/chrys/orchestration/engine/run/runner.py
@@ -785,6 +785,13 @@
         reference = parse_skill_reference(text, skill_details or self._current.manifest.runtime_details.skill_details)
         if reference is None:
             return None
+        # AIxCoding telemetry: record input skill (src/chrys/orchestration/aixcoding/telemetry)
+        try:
+            from chrys.orchestration.aixcoding.telemetry.skills import record_skill_reference
+
+            record_skill_reference(reference.skill.name, self._session)
+        except Exception:
+            pass
         return format_skill_reference_reminder(reference)
 
     def _complete_finalized_run(self, outcome: PostRunOutcome) -> str | None:
```

### `src/chrys/orchestration/invoker/kernel.py`

```diff
--- a/src/chrys/orchestration/invoker/kernel.py
+++ b/src/chrys/orchestration/invoker/kernel.py
@@ -291,6 +291,14 @@
         invocation_token = invocation_routing_key.set(invocation_id)
         # The tool calls of this pass start background commands for, and sleep on those of, this agent.
         scope_token = current_scope.set(TaskScope.of(request.origin))
+        # AIxCoding telemetry: bind pass (src/chrys/kernel/aixcoding/telemetry)
+        reset_telemetry_pass: Callable[[], None] | None = None
+        try:
+            from chrys.kernel.aixcoding.telemetry.context import bind_pass
+
+            reset_telemetry_pass = bind_pass(request.origin, handle.pass_id)
+        except Exception:
+            pass
         response: AgentResponse[Any] | None = None
         error: Exception | None = None
         cancellation: asyncio.CancelledError | None = None
@@ -392,6 +400,9 @@
                 # Pair only the cancellation this pass issued, never the
                 # operation shell's or an external caller's cancellation count.
                 task.uncancel()
+            # AIxCoding telemetry: reset pass (src/chrys/kernel/aixcoding/telemetry)
+            if reset_telemetry_pass is not None:
+                reset_telemetry_pass()
             current_invocation_origin.reset(origin_token)
             invocation_routing_key.reset(invocation_token)
             current_scope.reset(scope_token)
```

### `src/chrys/orchestration/sub_agents/tools.py`

```diff
--- a/src/chrys/orchestration/sub_agents/tools.py
+++ b/src/chrys/orchestration/sub_agents/tools.py
@@ -433,7 +433,15 @@
                 route_parts=(tool_name, profile.name),
                 model_profile=sub_active_profile,
             )
-            client = await create_client(
+            # AIxCoding telemetry: build agent context (src/chrys/service/aixcoding/telemetry)
+            client_factory = create_client
+            try:
+                from chrys.service.aixcoding.telemetry.model import for_agent_build
+
+                client_factory = for_agent_build(create_client, profile.name, self._workspace_cwd)
+            except Exception:
+                pass
+            client = await client_factory(
                 sub_active_profile,
                 session_id=sub_agent_session_id,
                 parent_session_id=self._session_id,
```

### `src/chrys/orchestration/workflows/agent_node_build.py`

```diff
--- a/src/chrys/orchestration/workflows/agent_node_build.py
+++ b/src/chrys/orchestration/workflows/agent_node_build.py
@@ -210,7 +210,15 @@
         raise RuntimeError("A kernel workflow node requires a model binding.")
     profile = binding.agent
     chat_options = effective_chat_options(model)
-    client = await create_client(
+    # AIxCoding telemetry: build agent context (src/chrys/service/aixcoding/telemetry)
+    client_factory = create_client
+    try:
+        from chrys.service.aixcoding.telemetry.model import for_agent_build
+
+        client_factory = for_agent_build(create_client, profile.name, res.workspace.primary_cwd)
+    except Exception:
+        pass
+    client = await client_factory(
         model,
         session_id=derive_llm_route_session_id(
             session_id,
```

### `src/chrys/service/agent_middleware/events/hosted_tools.py`

```diff
--- a/src/chrys/service/agent_middleware/events/hosted_tools.py
+++ b/src/chrys/service/agent_middleware/events/hosted_tools.py
@@ -80,6 +80,8 @@
     status: str
     phase: str
     retry_safety: str
     metadata: dict[str, Any]
+    # AIxCoding telemetry: hosted view source (src/chrys/service/aixcoding/telemetry)
+    model_source_id: str | None = None
 
 
@@ -523,7 +525,14 @@
 
 def adapt_hosted_tool(call: Content | None, result: Content | None = None) -> HostedToolView:
     """Adapt a canonical hosted call and optional paired result."""
-    return get_hosted_adapter(_family_for(call or result)).adapt(call, result)
+    # AIxCoding telemetry: adapt hosted source (src/chrys/kernel/aixcoding/telemetry)
+    view = get_hosted_adapter(_family_for(call or result)).adapt(call, result)
+    try:
+        from chrys.kernel.aixcoding.telemetry.provenance import hosted_source
+
+        return replace(view, model_source_id=hosted_source(call, result))
+    except Exception:
+        return view
 
 
 def hosted_replay_status(view: HostedToolView, *, has_result: bool) -> str:
```

### `src/chrys/service/agent_middleware/events/sub_agent_events.py`

```diff
--- a/src/chrys/service/agent_middleware/events/sub_agent_events.py
+++ b/src/chrys/service/agent_middleware/events/sub_agent_events.py
@@ -292,7 +292,9 @@
                     args=view.arguments,
                     provider_item_type=view.provider_item_type,
                     provider_call_id=view.provider_call_id,
+                    # AIxCoding telemetry: publish hosted source (src/chrys/service/aixcoding/telemetry)
                     provider_status=view.provider_status,
+                    model_source_id=view.model_source_id,
                 )
             )
             # A hosted call never passes this middleware's ``process``, which counts the local ones.
@@ -581,6 +583,8 @@
 
         # Pre-execution mutation tracking
         _meta = context.metadata if isinstance(context.metadata, dict) else {}
+        # AIxCoding telemetry: capture tool operation (src/chrys/service/aixcoding/telemetry)
+        operation_id = tool_operation_id(_meta)
         pre_rejected = bool(_meta.get(_APPROVAL_REJECTED_KEY))
         mut_ctx = None
         if not pre_rejected:
@@ -602,6 +606,11 @@
                     agent_name=self._agent_name,
                     tool_name=tool_name,
                     tool_kind=tool_kind,
+                    # AIxCoding telemetry: publish local start (src/chrys/service/aixcoding/telemetry)
+                    provider_call_id=provider_call_id,
+                    tool_operation_id=operation_id,
+                    agent_profile_name=self._profile_name or "",
+                    workspace_cwd=self._workspace_cwd or "",
                     args=args,
                     call_id=call_id,
                     session_id=self._session_id,
@@ -892,6 +901,9 @@
                             agent_name=self._agent_name,
                             tool_name=tool_name,
                             call_id=call_id,
+                            # AIxCoding telemetry: publish local result (src/chrys/service/aixcoding/telemetry)
+                            provider_call_id=provider_call_id,
+                            tool_operation_id=operation_id,
                             result=result_text,
                             image_contents=result_images,
                             duration_ms=duration_ms,
```

### `src/chrys/service/agent_middleware/events/tool_events.py`

```diff
--- a/src/chrys/service/agent_middleware/events/tool_events.py
+++ b/src/chrys/service/agent_middleware/events/tool_events.py
@@ -347,6 +347,8 @@
 
         # Pre-execution mutation tracking
         _meta = context.metadata if isinstance(context.metadata, dict) else {}
+        # AIxCoding telemetry: capture tool operation (src/chrys/service/aixcoding/telemetry)
+        operation_id = tool_operation_id(_meta)
         pre_rejected = bool(_meta.get(_APPROVAL_REJECTED_KEY))
         mut_ctx = None
         if not pre_rejected:
@@ -368,6 +370,11 @@
                     origin=origin,
                     tool_name=tool_name,
                     tool_kind=tool_kind,
+                    # AIxCoding telemetry: publish local start (src/chrys/service/aixcoding/telemetry)
+                    provider_call_id=provider_call_id,
+                    tool_operation_id=operation_id,
+                    agent_profile_name=self._profile_name or "",
+                    workspace_cwd=self._workspace_cwd or "",
                     args=args,
                     call_id=call_id,
                     session_id=self._session_id,
@@ -737,6 +744,9 @@
                             origin=origin,
                             tool_name=tool_name,
                             call_id=call_id,
+                            # AIxCoding telemetry: publish local result (src/chrys/service/aixcoding/telemetry)
+                            provider_call_id=provider_call_id,
+                            tool_operation_id=operation_id,
                             result=result_text,
                             image_contents=result_images,
                             duration_ms=duration_ms,
```

### `src/chrys/service/agent_middleware/response_validation.py`

```diff
--- a/src/chrys/service/agent_middleware/response_validation.py
+++ b/src/chrys/service/agent_middleware/response_validation.py
@@ -340,7 +340,8 @@
             if commit not in self._hosted_commit_keys_in_flight:
                 self._hosted_commit_keys_in_flight.append(commit)
 
-    async def _observe_failed_response(self, error: ProviderResponseError) -> None:
+    # AIxCoding telemetry: failed observation source (src/chrys/service/aixcoding/telemetry)
+    async def _observe_failed_response(self, error: ProviderResponseError, source_id: str | None) -> None:
         """Count the hosted work a failed response showed but never yielded.
 
         The adapter raised before the response landed, so this is the only
@@ -348,11 +349,23 @@
         """
         if contents := list(error.observed_contents):
             self._observe_hosted_contents(contents)
-            await self._notify_contents_observed(contents, is_final=True, failed=True)
-
-    async def _notify_contents_observed(self, contents: Sequence[Any], *, is_final: bool, failed: bool = False) -> None:
+            # AIxCoding telemetry: forward failure source (src/chrys/service/aixcoding/telemetry)
+            await self._notify_contents_observed(contents, is_final=True, failed=True, source_id=source_id)
+
+    # AIxCoding telemetry: observation source parameter (src/chrys/service/aixcoding/telemetry)
+    async def _notify_contents_observed(
+        self, contents: Sequence[Any], *, is_final: bool, failed: bool = False, source_id: str | None = None
+    ) -> None:
         if self._observation_hook is None or in_internal_side_call():
             return
+        # AIxCoding telemetry: remember hosted source (src/chrys/kernel/aixcoding/telemetry)
+        if source_id is not None:
+            try:
+                from chrys.kernel.aixcoding.telemetry.provenance import remember_hosted_source
+
+                remember_hosted_source(contents, source_id)
+            except Exception:
+                pass
         try:
             await self._observation_hook.observe_contents(contents, is_final=is_final, failed=failed)
         except Exception:
@@ -407,7 +420,8 @@
         try:
             await call_next()
         except ProviderResponseError as error:
-            await self._observe_failed_response(error)
+            # AIxCoding telemetry: bind blocking failure (src/chrys/service/aixcoding/telemetry)
+            await self._observe_failed_response(error, context.model_source_id)
             raise
         result = context.result
         if context.stream:
@@ -419,19 +433,27 @@
                 # A provider stream that failed after showing hosted work:
                 # the error carries what never reached an update.
                 if isinstance(error := _stream_error_of(stream), ProviderResponseError):
-                    await self._observe_failed_response(error)
+                    # AIxCoding telemetry: bind stream failure (src/chrys/service/aixcoding/telemetry)
+                    await self._observe_failed_response(error, context.model_source_id)
 
             async def _conclude(response: ChatResponse) -> None:
                 await self._conclude(context, response, validation)
 
-            stream.with_transform_hook(self._observe_update)
+            # AIxCoding telemetry: capture stream source (src/chrys/service/aixcoding/telemetry)
+            async def _observe(update: ChatResponseUpdate) -> ChatResponseUpdate | None:
+                return await self._observe_update(update, context.model_source_id)
+
+            stream.with_transform_hook(_observe)
             stream.with_cleanup_hook(_observe_failure)
             stream.with_result_hook(_conclude)
             return
         if isinstance(result, ChatResponse):
             await self._conclude(context, result, validation)
 
-    async def _observe_update(self, update: ChatResponseUpdate) -> ChatResponseUpdate | None:
+    # AIxCoding telemetry: stream source parameter (src/chrys/service/aixcoding/telemetry)
+    async def _observe_update(
+        self, update: ChatResponseUpdate, source_id: str | None = None
+    ) -> ChatResponseUpdate | None:
         """Record the hosted work one streamed update shows, as it arrives."""
         if isinstance(evidence := update.raw_representation, HeldHostedEvidence):
             # Hosted work the adapter holds behind an unfinished call already
@@ -441,14 +463,16 @@
             return ChatResponseUpdate.transport_heartbeat()
         contents = list(update.contents or [])
         self._observe_hosted_contents(contents)
-        await self._notify_contents_observed(contents, is_final=False)
+        # AIxCoding telemetry: forward stream source (src/chrys/service/aixcoding/telemetry)
+        await self._notify_contents_observed(contents, is_final=False, source_id=source_id)
         return None
 
     async def _conclude(self, context: ChatContext, response: ChatResponse, validation: ValidationTrace | None) -> None:
         """Judge a landed response: keep it, or fail the turn with the reason."""
         contents = [content for message in response.messages or [] for content in message.contents]
         self._observe_hosted_contents(contents)
-        await self._notify_contents_observed(contents, is_final=True)
+        # AIxCoding telemetry: forward terminal source (src/chrys/service/aixcoding/telemetry)
+        await self._notify_contents_observed(contents, is_final=True, source_id=context.model_source_id)
         if response.continuation_token is not None:
             # A background response still running: the poll that finishes it is judged.
             await self._notify_attempt_accepted(response.messages or [])
```

### `src/chrys/service/llm/clients.py`

```diff
--- a/src/chrys/service/llm/clients.py
+++ b/src/chrys/service/llm/clients.py
@@ -636,8 +636,17 @@
             use_route_session_context=use_route_session_context,
         ),
     )
+    # AIxCoding telemetry: assemble model middleware (src/chrys/service/aixcoding/telemetry)
+    telemetry_middleware = None
+    try:
+        from chrys.service.aixcoding.telemetry.model import build_middleware
+
+        telemetry_middleware = build_middleware(parent_session_id or session_id)
+    except Exception:
+        pass
     return ToolLoopLayer(
-        ChatMiddlewareLayer(wire_client),
+        # AIxCoding telemetry: install model middleware (src/chrys/service/aixcoding/telemetry)
+        ChatMiddlewareLayer(wire_client, middleware=telemetry_middleware),
         max_iterations=max_iterations,
         max_consecutive_errors=max_consecutive_errors,
         tool_result_ceiling_tokens=tool_result_ceiling_tokens,
```

### `tests/architecture/trajectory_wait_manifest.json`

```diff
--- a/tests/architecture/trajectory_wait_manifest.json
+++ b/tests/architecture/trajectory_wait_manifest.json
@@ -646,7 +646,7 @@
         ["awaitable", "await _progress(AGENT_LOAD_PHASE_MODEL, 'Resolving model profile', status=AGENT_LOAD_STATUS_RUNNING)", "unresolved"],
         ["awaitable", "await _progress(AGENT_LOAD_PHASE_RUNTIME, 'Capturing workspace context', status=AGENT_LOAD_STATUS_RUNNING)", "unresolved"],
         ["awaitable", "await bus.publish(Warning(code='protected_chat_options_stripped', message=protected_options_warning.message, display_message=_BUILDER_PROTECTED_CHAT_OPTIONS_STRIPPED.bind(keys=', '.join(protected_options_warning.keys)), session_id=session_id))", "unresolved"],
-        ["wrapper", "await create_client(active_profile, on_intermediate_text=on_intermediate, session_id=session_id, session_dir=effective_session_dir, tool_result_ceiling_tokens=settings.tool_result_ceiling_tokens)", "unresolved", "chrys.service.llm.clients.create_client"],
+        ["awaitable", "await client_factory(active_profile, on_intermediate_text=on_intermediate, session_id=session_id, session_dir=effective_session_dir, tool_result_ceiling_tokens=settings.tool_result_ceiling_tokens)", "unresolved"],
         ["awaitable", "await prepared.own_or_release(client.aclose)", "unresolved"],
         ["awaitable", "await _progress(AGENT_LOAD_PHASE_TOOLS, 'Loading built-in tools', status=AGENT_LOAD_STATUS_RUNNING)", "unresolved"],
         ["wrapper", "await import_off_loop(*tool_packs.IMPLEMENTATION_MODULES)", "unresolved", "chrys.foundation.util.imports.import_off_loop"],
@@ -778,6 +778,7 @@
       "AgentEngine._release_resources": [
         ["awaitable", "await self._side_questions.close()", "unresolved"],
         ["awaitable", "await self._lifecycle.shutdown()", "unresolved"],
+        ["awaitable", "await detach(self._bus)", "unresolved"],
         ["awaitable", "await self._hook_confirmations.close()", "unresolved"]
       ],
       "AgentEngine._session_operation": [
@@ -810,6 +811,7 @@
         ["awaitable", "await self._bus.subscribe(InvocationResumed, self._on_sub_agent_unpaused)", "unresolved"],
         ["awaitable", "await self._bus.subscribe(InvocationAborted, self._on_sub_agent_unpaused)", "unresolved"],
         ["awaitable", "await self._bus.subscribe(InvocationCascadeAborted, self._on_sub_agent_unpaused)", "unresolved"],
+        ["awaitable", "await attach(self._bus)", "unresolved"],
         ["awaitable", "await self._workflows.subscribe()", "unresolved"],
         ["awaitable", "await self._side_questions.subscribe()", "unresolved"],
         ["awaitable", "await self._hook_confirmations.start()", "unresolved"]
@@ -1112,7 +1114,7 @@
       ],
       "TurnBindings._publish_hosted_operation": [
         ["awaitable", "await emitter.publish(InvocationMessage(origin=emitter.origin, text=operation.text, is_final=True, structured_output_completed=operation.structured_output_completed, **self._assistant_message_event_kwargs(), session_id=self._session_id))", "unresolved"],
-        ["awaitable", "await emitter.publish(InvocationToolCallStart(origin=emitter.origin, tool_name=view.tool_name, call_id=operation.presentation_id, provider_hosted=True, hosted_family=view.family, provider=view.provider, provider_item_type=view.provider_item_type, provider_call_id=view.provider_call_id, provider_status=view.provider_status, tool_kind=HOSTED_TOOL_DEFAULT_KIND_BY_FAMILY.get(view.family, ''), args=view.arguments, session_id=self._session_id))", "unresolved"],
+        ["awaitable", "await emitter.publish(InvocationToolCallStart(origin=emitter.origin, tool_name=view.tool_name, call_id=operation.presentation_id, provider_hosted=True, hosted_family=view.family, provider=view.provider, provider_item_type=view.provider_item_type, provider_call_id=view.provider_call_id, provider_status=view.provider_status, model_source_id=view.model_source_id, tool_kind=HOSTED_TOOL_DEFAULT_KIND_BY_FAMILY.get(view.family, ''), args=view.arguments, session_id=self._session_id))", "unresolved"],
         ["awaitable", "await emitter.publish(InvocationToolCallArgsUpdated(origin=emitter.origin, tool_name=view.tool_name, call_id=operation.presentation_id, provider_hosted=True, hosted_family=view.family, provider=view.provider, provider_item_type=view.provider_item_type, provider_call_id=view.provider_call_id, provider_status=view.provider_status, tool_kind=HOSTED_TOOL_DEFAULT_KIND_BY_FAMILY.get(view.family, ''), args=view.arguments, session_id=self._session_id))", "unresolved"],
         ["awaitable", "await emitter.publish(InvocationToolCallProgress(origin=emitter.origin, tool_name=view.tool_name, call_id=operation.presentation_id, provider_hosted=True, hosted_family=view.family, provider=view.provider, provider_item_type=view.provider_item_type, provider_call_id=view.provider_call_id, provider_status=view.provider_status, lines=view.result_text.splitlines(), image_contents=view.image_contents, snapshot_metadata=view.metadata, session_id=self._session_id))", "unresolved"],
         ["awaitable", "await emitter.publish(InvocationToolCallStatusUpdated(origin=emitter.origin, tool_name=view.tool_name, call_id=operation.presentation_id, provider_hosted=True, hosted_family=view.family, provider=view.provider, status=view.status, provider_status=view.provider_status, metadata=metadata, session_id=self._session_id))", "unresolved"],
@@ -2756,7 +2758,7 @@
         ["wrapper", "await rollback_resources(prepared)", "unresolved", "chrys.orchestration.invoker.resources.rollback_resources"]
       ],
       "SubAgentTools.register._acquire": [
-        ["wrapper", "await create_client(sub_active_profile, session_id=sub_agent_session_id, parent_session_id=self._session_id, use_route_session_context=True, session_dir=self._session_dir, tool_result_ceiling_tokens=self._tool_result_ceiling_tokens)", "unresolved", "chrys.service.llm.clients.create_client"],
+        ["awaitable", "await client_factory(sub_active_profile, session_id=sub_agent_session_id, parent_session_id=self._session_id, use_route_session_context=True, session_dir=self._session_dir, tool_result_ceiling_tokens=self._tool_result_ceiling_tokens)", "unresolved"],
         ["awaitable", "await prepared.own_or_release(client.aclose)", "unresolved"],
         ["awaitable", "await tool_packs.assemble_tools(tool_build)", "unresolved"],
         ["awaitable", "await self._bus.publish(warning)", "unresolved"],
@@ -2921,7 +2923,7 @@
         ["awaitable", "await sub_agent_tools.register(ref, sub_profile, environment, settings=res.settings, fallback_profile=model, model_registry=res.model_registry)", "unresolved"]
       ],
       "build_kernel_node": [
-        ["wrapper", "await create_client(model, session_id=derive_llm_route_session_id(session_id, route_kind='workflow-node', route_parts=(node_id, profile.name, invocation_id), model_profile=model), parent_session_id=session_id, session_dir=res.session_dir, tool_result_ceiling_tokens=res.settings.tool_result_ceiling_tokens)", "unresolved", "chrys.service.llm.clients.create_client"],
+        ["awaitable", "await client_factory(model, session_id=derive_llm_route_session_id(session_id, route_kind='workflow-node', route_parts=(node_id, profile.name, invocation_id), model_profile=model), parent_session_id=session_id, session_dir=res.session_dir, tool_result_ceiling_tokens=res.settings.tool_result_ceiling_tokens)", "unresolved"],
         ["awaitable", "await conversation.own_or_release(client.aclose)", "unresolved"],
         ["awaitable", "await tool_packs.assemble_tools(tool_build)", "unresolved"],
         ["awaitable", "await res.bus.publish(warning)", "unresolved"],
@@ -3898,7 +3900,7 @@
       ],
       "SubAgentEventMiddleware._process_tool_call": [
         ["wrapper", "await prepare_mutation_tracking(self._mutation_tracker, tool_name, args, call_id, is_shell, workspace_cwd=self._workspace_cwd, coordinator=self._mutation_coordinator, tool_operation_id=tool_operation_id(_meta))", "unresolved", "chrys.service.mutations.pipeline.prepare_mutation_tracking"],
-        ["awaitable", "await self._bus.publish(InvocationToolCallStart(origin=origin, agent_name=self._agent_name, tool_name=tool_name, tool_kind=tool_kind, args=args, call_id=call_id, session_id=self._session_id))", "unresolved"],
+        ["awaitable", "await self._bus.publish(InvocationToolCallStart(origin=origin, agent_name=self._agent_name, tool_name=tool_name, tool_kind=tool_kind, provider_call_id=provider_call_id, tool_operation_id=operation_id, agent_profile_name=self._profile_name or '', workspace_cwd=self._workspace_cwd or '', args=args, call_id=call_id, session_id=self._session_id))", "unresolved"],
         ["awaitable", "await self._hosted_bridge.local_call_start_published(provider_call_id)", "unresolved"],
         ["awaitable", "await preamble.finished(outcome=PreparationOutcome.HANDOFF)", "unresolved"],
         ["awaitable", "await trajectory.started(tool_name=tool_name, tool_kind=tool_kind, batch_index=None, invocation_order=get_tool_invocation_order(context), arguments=args, invocation_metadata=_meta, tool_context=resolve_tool_call_context(context.function, args) or None, preamble_operation_id=preamble.operation_id if preamble is not None and preamble.start_committed else None)", "unresolved"],
@@ -3906,14 +3908,14 @@
         ["wrapper", "await finalize_mutation_tracking(self._mutation_tracker, mut_ctx, call_id, coordinator=self._mutation_coordinator, tool_errored=tool_failed)", "unresolved", "chrys.service.mutations.pipeline.finalize_mutation_tracking"],
         ["wrapper", "await apply_after_tool_extensions(self._extension_hooks, context, tool_name=tool_name, kind=tool_kind, call_id=call_id, args=args, result_text=result_text, raised_text=raised_text, failed=errored or structured_failed or rejected, rejected=rejected, duration_ms=duration_ms)", "unresolved", "chrys.service.agent_middleware.events.hook_dispatch.apply_after_tool_extensions"],
         ["wrapper", "await fire_after_tool_hooks(manager=self._hook_manager, session_id=self._session_id, profile_name=self._profile_name, tool_name=tool_name, kind=tool_kind, call_id=call_id, args=args, result_text=result_text, duration_ms=duration_ms, errored=errored, failed=structured_failed, approval_rejected=rejected, rejection_source=source, hook_confirmation=hook_confirmation(_meta), workspace_cwd=self._workspace_cwd, target_operation_id=trajectory.operation_id if trajectory is not None else None, origin=origin)", "unresolved", "chrys.service.agent_middleware.events.hook_dispatch.fire_after_tool_hooks"],
-        ["awaitable", "await self._bus.publish(InvocationToolCallResult(origin=origin, agent_name=self._agent_name, tool_name=tool_name, call_id=call_id, result=result_text, image_contents=result_images, duration_ms=duration_ms, metadata=metadata, session_id=self._session_id))", "unresolved"],
+        ["awaitable", "await self._bus.publish(InvocationToolCallResult(origin=origin, agent_name=self._agent_name, tool_name=tool_name, call_id=call_id, provider_call_id=provider_call_id, tool_operation_id=operation_id, result=result_text, image_contents=result_images, duration_ms=duration_ms, metadata=metadata, session_id=self._session_id))", "unresolved"],
         ["awaitable", "await trajectory.payload_observed(result_text=preview_result_ceiling(result_text, self._tool_result_ceiling_tokens, observation=payload_observation), image_count=len(result_images), observation=payload_observation)", "unresolved"],
         ["awaitable", "await trajectory.finished(outcome=tool_outcome(cancelled=False, rejected=rejected, errored=errored, result_metadata=metadata), duration_ms=elapsed_ms, result_metadata=metadata, error_kind=raised_error_kind)", "unresolved"],
         ["wrapper", "await self._publish_progress()", "unresolved", "chrys.service.agent_middleware.events.sub_agent_events.SubAgentEventMiddleware._publish_progress"]
       ],
       "SubAgentEventMiddleware._publish_hosted_operation": [
         ["awaitable", "await self._end_text_segment('failed' if bridge.shows_failed_attempt else 'completed')", "unresolved"],
-        ["awaitable", "await self._bus.publish(InvocationToolCallStart(origin=origin, **common, tool_kind=HOSTED_TOOL_DEFAULT_KIND_BY_FAMILY.get(view.family, ''), args=view.arguments, provider_item_type=view.provider_item_type, provider_call_id=view.provider_call_id, provider_status=view.provider_status))", "unresolved"],
+        ["awaitable", "await self._bus.publish(InvocationToolCallStart(origin=origin, **common, tool_kind=HOSTED_TOOL_DEFAULT_KIND_BY_FAMILY.get(view.family, ''), args=view.arguments, provider_item_type=view.provider_item_type, provider_call_id=view.provider_call_id, provider_status=view.provider_status, model_source_id=view.model_source_id))", "unresolved"],
         ["wrapper", "await self._publish_progress()", "unresolved", "chrys.service.agent_middleware.events.sub_agent_events.SubAgentEventMiddleware._publish_progress"],
         ["awaitable", "await self._bus.publish(InvocationToolCallArgsUpdated(origin=origin, **common, tool_kind=HOSTED_TOOL_DEFAULT_KIND_BY_FAMILY.get(view.family, ''), args=view.arguments, provider_item_type=view.provider_item_type, provider_call_id=view.provider_call_id, provider_status=view.provider_status))", "unresolved"],
         ["awaitable", "await self._bus.publish(InvocationToolCallProgress(origin=origin, **common, lines=view.result_text.splitlines(), image_contents=view.image_contents, snapshot_metadata=view.metadata, provider_item_type=view.provider_item_type, provider_call_id=view.provider_call_id, provider_status=view.provider_status))", "unresolved"],
@@ -3959,7 +3961,7 @@
       ],
       "ToolEventMiddleware._process_tool_call": [
         ["wrapper", "await prepare_mutation_tracking(self._mutation_tracker, tool_name, args, call_id, is_shell, workspace_cwd=self._workspace_cwd, coordinator=self._mutation_coordinator, tool_operation_id=tool_operation_id(_meta))", "unresolved", "chrys.service.mutations.pipeline.prepare_mutation_tracking"],
-        ["awaitable", "await self._bus.publish(InvocationToolCallStart(origin=origin, tool_name=tool_name, tool_kind=tool_kind, args=args, call_id=call_id, session_id=self._session_id))", "unresolved"],
+        ["awaitable", "await self._bus.publish(InvocationToolCallStart(origin=origin, tool_name=tool_name, tool_kind=tool_kind, provider_call_id=provider_call_id, tool_operation_id=operation_id, agent_profile_name=self._profile_name or '', workspace_cwd=self._workspace_cwd or '', args=args, call_id=call_id, session_id=self._session_id))", "unresolved"],
         ["awaitable", "await self._on_start_published(provider_call_id)", "unresolved"],
         ["awaitable", "await bus.subscribe(ShellToBackground, move_to_background)", "unresolved"],
         ["awaitable", "await preamble.finished(outcome=PreparationOutcome.HANDOFF)", "unresolved"],
@@ -3969,7 +3971,7 @@
         ["wrapper", "await finalize_mutation_tracking(self._mutation_tracker, mut_ctx, call_id, coordinator=self._mutation_coordinator, tool_errored=tool_failed)", "unresolved", "chrys.service.mutations.pipeline.finalize_mutation_tracking"],
         ["wrapper", "await apply_after_tool_extensions(self._extension_hooks, context, tool_name=tool_name, kind=tool_kind, call_id=call_id, args=args, result_text=result_text, raised_text=raised_text, failed=errored or structured_failed or rejected, rejected=rejected, duration_ms=duration_ms)", "unresolved", "chrys.service.agent_middleware.events.hook_dispatch.apply_after_tool_extensions"],
         ["wrapper", "await fire_after_tool_hooks(manager=self._hook_manager, session_id=self._session_id, profile_name=self._profile_name, tool_name=tool_name, kind=tool_kind, call_id=call_id, args=args, result_text=result_text, duration_ms=duration_ms, errored=errored, failed=structured_failed, approval_rejected=rejected, rejection_source=source, hook_confirmation=hook_confirmation(_meta), workspace_cwd=self._workspace_cwd, target_operation_id=trajectory.operation_id if trajectory is not None else None)", "unresolved", "chrys.service.agent_middleware.events.hook_dispatch.fire_after_tool_hooks"],
-        ["awaitable", "await self._bus.publish(InvocationToolCallResult(origin=origin, tool_name=tool_name, call_id=call_id, result=result_text, image_contents=result_images, duration_ms=duration_ms, session_id=self._session_id, metadata=metadata))", "unresolved"],
+        ["awaitable", "await self._bus.publish(InvocationToolCallResult(origin=origin, tool_name=tool_name, call_id=call_id, provider_call_id=provider_call_id, tool_operation_id=operation_id, result=result_text, image_contents=result_images, duration_ms=duration_ms, session_id=self._session_id, metadata=metadata))", "unresolved"],
         ["awaitable", "await trajectory.payload_observed(result_text=preview_result_ceiling(result_text, self._tool_result_ceiling_tokens, observation=payload_observation), image_count=len(result_images), observation=payload_observation)", "unresolved"],
         ["awaitable", "await trajectory.finished(outcome=tool_outcome(cancelled=False, rejected=rejected, errored=errored, result_metadata=metadata), duration_ms=elapsed_ms, result_metadata=metadata, error_kind=raised_error_kind)", "unresolved"]
       ],
@@ -4004,7 +4006,7 @@
     },
     "chrys.service.agent_middleware.response_validation": {
       "ResponseValidationMiddleware._conclude": [
-        ["wrapper", "await self._notify_contents_observed(contents, is_final=True)", "unresolved", "chrys.service.agent_middleware.response_validation.ResponseValidationMiddleware._notify_contents_observed"],
+        ["wrapper", "await self._notify_contents_observed(contents, is_final=True, source_id=context.model_source_id)", "unresolved", "chrys.service.agent_middleware.response_validation.ResponseValidationMiddleware._notify_contents_observed"],
         ["wrapper", "await self._notify_attempt_accepted(response.messages or [])", "unresolved", "chrys.service.agent_middleware.response_validation.ResponseValidationMiddleware._notify_attempt_accepted"],
         ["awaitable", "await validation.finished(accepted=verdict.ok, reason_code=None if verdict.ok else verdict.code)", "unresolved"],
         ["wrapper", "await self._notify_attempt_rejected(verdict.reason)", "unresolved", "chrys.service.agent_middleware.response_validation.ResponseValidationMiddleware._notify_attempt_rejected"],
@@ -4026,23 +4028,26 @@
         ["awaitable", "await self._observation_hook.begin_response()", "unresolved"]
       ],
       "ResponseValidationMiddleware._observe_failed_response": [
-        ["wrapper", "await self._notify_contents_observed(contents, is_final=True, failed=True)", "unresolved", "chrys.service.agent_middleware.response_validation.ResponseValidationMiddleware._notify_contents_observed"]
+        ["wrapper", "await self._notify_contents_observed(contents, is_final=True, failed=True, source_id=source_id)", "unresolved", "chrys.service.agent_middleware.response_validation.ResponseValidationMiddleware._notify_contents_observed"]
       ],
       "ResponseValidationMiddleware._observe_update": [
-        ["wrapper", "await self._notify_contents_observed(contents, is_final=False)", "unresolved", "chrys.service.agent_middleware.response_validation.ResponseValidationMiddleware._notify_contents_observed"]
+        ["wrapper", "await self._notify_contents_observed(contents, is_final=False, source_id=source_id)", "unresolved", "chrys.service.agent_middleware.response_validation.ResponseValidationMiddleware._notify_contents_observed"]
       ],
       "ResponseValidationMiddleware.process": [
         ["wrapper", "await self._notify_response_started(continuation=continuation)", "unresolved", "chrys.service.agent_middleware.response_validation.ResponseValidationMiddleware._notify_response_started"],
         ["wrapper", "await self._notify_attempt_started(continuation=continuation)", "unresolved", "chrys.service.agent_middleware.response_validation.ResponseValidationMiddleware._notify_attempt_started"],
         ["awaitable", "await call_next()", "unresolved"],
-        ["wrapper", "await self._observe_failed_response(error)", "unresolved", "chrys.service.agent_middleware.response_validation.ResponseValidationMiddleware._observe_failed_response"],
+        ["wrapper", "await self._observe_failed_response(error, context.model_source_id)", "unresolved", "chrys.service.agent_middleware.response_validation.ResponseValidationMiddleware._observe_failed_response"],
         ["wrapper", "await self._conclude(context, result, validation)", "unresolved", "chrys.service.agent_middleware.response_validation.ResponseValidationMiddleware._conclude"]
       ],
       "ResponseValidationMiddleware.process._conclude": [
         ["wrapper", "await self._conclude(context, response, validation)", "unresolved", "chrys.service.agent_middleware.response_validation.ResponseValidationMiddleware._conclude"]
       ],
+      "ResponseValidationMiddleware.process._observe": [
+        ["wrapper", "await self._observe_update(update, context.model_source_id)", "unresolved", "chrys.service.agent_middleware.response_validation.ResponseValidationMiddleware._observe_update"]
+      ],
       "ResponseValidationMiddleware.process._observe_failure": [
-        ["wrapper", "await self._observe_failed_response(error)", "unresolved", "chrys.service.agent_middleware.response_validation.ResponseValidationMiddleware._observe_failed_response"]
+        ["wrapper", "await self._observe_failed_response(error, context.model_source_id)", "unresolved", "chrys.service.agent_middleware.response_validation.ResponseValidationMiddleware._observe_failed_response"]
       ]
     },
     "chrys.service.agent_middleware.system_reminder": {
```

## 异步等待清单

用上游扫描器在候选源码上生成。新增或重新打开的条目按上游工具默认规则初始化。下表列出原规则和拟定规则。已审规则仅在仍满足原判据时恢复。

| 等待位置 | 原规则 | 拟定规则 |
| --- | --- | --- |
| `chrys.orchestration.engine.build.builder:build_agent._acquire:4` | wrapper（`chrys.service.llm.clients.create_client`） | awaitable（`client_factory` 不再解析到原工厂） |
| `chrys.orchestration.engine.engine:AgentEngine._release_resources:1` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._release_resources:2` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._release_resources:3` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._release_resources:4` | 新增 | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:1` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:2` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:3` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:4` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:5` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:6` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:7` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:8` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:9` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:10` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:11` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:12` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:13` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:14` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:15` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:16` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:17` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:18` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:19` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:20` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:21` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:22` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:23` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:24` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:25` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:26` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:27` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:28` | unresolved | unresolved |
| `chrys.orchestration.engine.engine:AgentEngine._subscribe_event_handlers:29` | 新增 | unresolved |
| `chrys.orchestration.engine.run.bindings:TurnBindings._publish_hosted_operation:2` | unresolved | unresolved |
| `chrys.orchestration.sub_agents.tools:SubAgentTools.register._acquire:1` | wrapper（`chrys.service.llm.clients.create_client`） | awaitable（`client_factory` 不再解析到原工厂） |
| `chrys.orchestration.workflows.agent_node_build:build_kernel_node:1` | wrapper（`chrys.service.llm.clients.create_client`） | awaitable（`client_factory` 不再解析到原工厂） |
| `chrys.service.agent_middleware.events.sub_agent_events:SubAgentEventMiddleware._process_tool_call:2` | unresolved | unresolved |
| `chrys.service.agent_middleware.events.sub_agent_events:SubAgentEventMiddleware._process_tool_call:10` | unresolved | unresolved |
| `chrys.service.agent_middleware.events.sub_agent_events:SubAgentEventMiddleware._publish_hosted_operation:2` | unresolved | unresolved |
| `chrys.service.agent_middleware.events.tool_events:ToolEventMiddleware._process_tool_call:2` | unresolved | unresolved |
| `chrys.service.agent_middleware.events.tool_events:ToolEventMiddleware._process_tool_call:12` | unresolved | unresolved |
| `chrys.service.agent_middleware.response_validation:ResponseValidationMiddleware._conclude:1` | unresolved | unresolved |
| `chrys.service.agent_middleware.response_validation:ResponseValidationMiddleware._observe_failed_response:1` | unresolved | unresolved |
| `chrys.service.agent_middleware.response_validation:ResponseValidationMiddleware._observe_update:1` | unresolved | unresolved |
| `chrys.service.agent_middleware.response_validation:ResponseValidationMiddleware.process:4` | unresolved | unresolved |
| `chrys.service.agent_middleware.response_validation:ResponseValidationMiddleware.process._observe:1` | 新增 | unresolved |
| `chrys.service.agent_middleware.response_validation:ResponseValidationMiddleware.process._observe_failure:1` | unresolved | unresolved |

三个构建入口改为经 `client_factory` 调用后，原有 `wrapper` 规则无法再解析到 `chrys.service.llm.clients.create_client`，条目降为 `awaitable` 并保留 `unresolved`（CI 允许）。代价是这三处不再受 wrapper 规则约束：工厂改为经定制包装器调用后，该 guard 不再校验实参或关闭归属。若需保持约束，可改为在 `create_client` 上追加显式参数（对应旧版 R2 稿），由负责人取舍。
