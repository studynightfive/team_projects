import { apiClient } from "../api/client";
import {
  unwrapApiData,
  type ApiResponse,
  type ApiSchema,
} from "../api/contracts";

export type UserIncentives = Readonly<ApiSchema<"UserIncentives">>;
export type ContributionItem = Readonly<ApiSchema<"ContributionItem">>;

export const getMyIncentives = async (
  params: {
    readonly page?: number;
    readonly page_size?: number;
  } = {},
  signal?: AbortSignal,
): Promise<UserIncentives> => {
  const response = await apiClient.get<ApiResponse<UserIncentives>>(
    "/v1/me/incentives",
    { params, signal },
  );
  return unwrapApiData(response.data);
};
