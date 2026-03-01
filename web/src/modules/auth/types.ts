export interface LoginResponse {
  token: string;
  user: {
    id: number;
    username: string;
    isGuest: boolean;
  };
  roles: string[];
  permissions: string[];
}

export interface LoginProps {
  onLogin: () => void;
}
