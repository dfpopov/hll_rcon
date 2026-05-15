import { cmd } from "@/utils/fetchUtils";

export const loader = async () => {
    const [whitelist, config] = await Promise.all([
        cmd.GET_VOTEMAP_SEEDING_WHITELIST(),
        cmd.GET_VOTEMAP_SEEDING_CONFIG(),
    ]);
    return { whitelist, config };
};
