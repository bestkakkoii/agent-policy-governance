import catalog from "./generated/policy_data.mjs";
import { create_registry } from "./handler.mjs";
export default create_registry(catalog);
