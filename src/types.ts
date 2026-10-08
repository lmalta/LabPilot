export type Role = "system" | "user" | "assistant" | "tool";

export interface MessageBase {
  role: Role;
  content: string;
}

export interface MessageSystem extends MessageBase {
  role: "system";
}

export interface MessageUser extends MessageBase {
  role: "user";
}

export interface MessageAssistant extends MessageBase {
  role: "assistant";
  tool_calls?: ToolCall[];
}

export interface MessageTool extends MessageBase {
  role: "tool";
  tool_name: string;
}

export type Message =
  | MessageSystem
  | MessageUser
  | MessageAssistant
  | MessageTool;

export interface ToolCall {
  function: {
    name: string;
    arguments: Record<string, unknown>;
  };
}
