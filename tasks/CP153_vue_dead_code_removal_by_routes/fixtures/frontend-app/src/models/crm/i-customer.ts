export interface ICustomer {
  id: string;
  name: string;
  company: string;
  phone: string;
  email: string;
  level: "vip" | "regular" | "potential";
}
