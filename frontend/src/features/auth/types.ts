export type AuthUser = {
  id: string;
  email: string;
  name: string;
  role: string;
  company_id: string;
  site_id: string | null;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: AuthUser;
};

export type RegisterPayload = {
  company_name: string;
  name: string;
  email: string;
  password: string;
};