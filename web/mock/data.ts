// Mock 数据集。
export const mockUser = {
  id: 1,
  username: "tester",
  is_guest: false,
};

export const mockRoles = ["translator"];
export const mockPermissions = ["text.read", "text.write", "dictionary.read", "dictionary.write"];

export const mockTexts = [
  {
    id: 101,
    fid: "file_a",
    part: "p1",
    source_text: "Hello {name}",
    translated_text: "你好 {name}",
    status: "待认领",
    edit_count: 1,
    updated_at: "2026-01-30T10:00:00Z",
    created_at: "2026-01-30T09:00:00Z",
  },
  {
    id: 102,
    fid: "file_b",
    part: "p2",
    source_text: "Orc %s!",
    translated_text: null,
    status: "待认领",
    edit_count: 0,
    updated_at: "2026-01-30T10:10:00Z",
    created_at: "2026-01-30T09:10:00Z",
  },
];

export const mockDictionary = [
  {
    id: 201,
    term_key: "orc",
    term_value: "兽人",
    category: "race",
    is_active: true,
    created_at: "2026-01-30T10:00:00Z",
    updated_at: "2026-01-30T10:00:00Z",
  },
];
