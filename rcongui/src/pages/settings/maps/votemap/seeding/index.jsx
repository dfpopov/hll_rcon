import { useMemo, useState, useEffect } from "react";
import {
  Box,
  Stack,
  Paper,
  Typography,
  Switch,
  FormControlLabel,
  TextField,
  Button,
  IconButton,
  Tooltip,
  LinearProgress,
  Divider,
  Alert,
  Tabs,
  Tab,
  Chip,
} from "@mui/material";
import RestoreIcon from "@mui/icons-material/Restore";
import SaveIcon from "@mui/icons-material/Save";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLoaderData, useRouteLoaderData } from "react-router-dom";
import { toast } from "react-toastify";
import {
  mapsManagerMutationOptions,
  mapsManagerQueryKeys,
  mapsManagerQueryOptions,
} from "../../queries";
import { MapWhitelistList } from "../../MapList";
import { MapBuilderListItem } from "../../MapListItem";
import MapListBuilder from "../../MapListBuilder";

/**
 * Votemap seeding-window settings page.
 *
 * Edits VotemapSeedingUserConfig (the Redis-backed config behind
 * custom_tools/votemap_seeding.py). When the seeding window is active
 * (player count below threshold OR Kyiv hour in [start, end)), votemap
 * picks options ONLY from the warfare + offensive lists configured here.
 *
 * Outside the seeding window, the regular Map Whitelist tab applies.
 */
function VotemapSeedingPage() {
  const { maps } = useRouteLoaderData("maps");
  const { whitelist, config } = useLoaderData();
  const queryClient = useQueryClient();

  // Live data (the loader-provided values seed the cache)
  const { data: liveWhitelist } = useQuery({
    ...mapsManagerQueryOptions.votemapSeedingWhitelist(),
    initialData: whitelist,
    staleTime: 5_000,
  });
  const { data: liveConfig } = useQuery({
    ...mapsManagerQueryOptions.votemapSeedingConfig(),
    initialData: config,
    staleTime: 5_000,
  });

  // ── Maps split into warfare-only and offensive-only pools ───────────
  // CRCON's `maps` includes warfare, offensive (long form), offensive
  // (short '_off_' form for Stmariedumont), and skirmish layers. We
  // split by id substring — keeps the picker focused on relevant variants.
  //
  // Also restrict to day/rain environments for seeding: the seeding window
  // is when the server is empty or late at night, and asymmetric/dark
  // layers (dusk, night, dawn, overcast) make a bad first impression on
  // the friend group that's just logging in to start the server.
  const SEEDING_WEATHERS = new Set(["day", "rain"]);
  const isSeedingFriendlyEnv = (m) =>
    SEEDING_WEATHERS.has(String(m.environment || "day").toLowerCase());
  const warfareMaps = useMemo(
    () => maps.filter((m) => /warfare/i.test(m.id) && isSeedingFriendlyEnv(m)),
    [maps]
  );
  const offensiveMaps = useMemo(
    () =>
      maps.filter(
        (m) =>
          (/offensive/i.test(m.id) || /_off_/i.test(m.id)) &&
          isSeedingFriendlyEnv(m)
      ),
    [maps]
  );

  const selectedWarfare = useMemo(
    () =>
      (liveWhitelist?.warfare || [])
        .map((id) => maps.find((m) => m.id === id))
        .filter(Boolean),
    [liveWhitelist, maps]
  );
  const selectedOffensive = useMemo(
    () =>
      (liveWhitelist?.offensive || [])
        .map((id) => maps.find((m) => m.id === id))
        .filter(Boolean),
    [liveWhitelist, maps]
  );

  // ── Mutations ────────────────────────────────────────────────────────
  const onSeedingError = (error) => {
    toast.error(
      <div>
        <span>{error?.name || "Error"}</span>
        <p>{error?.message || "Request failed"}</p>
      </div>
    );
  };

  const invalidateSeedingWhitelist = () =>
    queryClient.invalidateQueries({
      queryKey: mapsManagerQueryKeys.votemapSeedingWhitelist,
    });

  const invalidateSeedingConfig = () =>
    queryClient.invalidateQueries({
      queryKey: mapsManagerQueryKeys.votemapSeedingConfig,
    });

  const { mutate: saveWarfare, isPending: isSavingWarfare } = useMutation({
    ...mapsManagerMutationOptions.setSeedingWhitelistWarfare,
    onSuccess: () => {
      invalidateSeedingWhitelist();
      toast.success("Seeding warfare whitelist saved");
    },
    onError: onSeedingError,
  });

  const { mutate: saveOffensive, isPending: isSavingOffensive } = useMutation({
    ...mapsManagerMutationOptions.setSeedingWhitelistOffensive,
    onSuccess: () => {
      invalidateSeedingWhitelist();
      toast.success("Seeding offensive whitelist saved");
    },
    onError: onSeedingError,
  });

  const { mutate: resetWhitelist, isPending: isResetting } = useMutation({
    ...mapsManagerMutationOptions.resetSeedingWhitelist,
    onSuccess: () => {
      invalidateSeedingWhitelist();
      toast.success("Seeding whitelist reset to defaults");
    },
    onError: onSeedingError,
  });

  const { mutate: saveConfig, isPending: isSavingConfig } = useMutation({
    ...mapsManagerMutationOptions.setSeedingConfig,
    onSuccess: () => {
      invalidateSeedingConfig();
      toast.success("Seeding settings saved");
    },
    onError: onSeedingError,
  });

  // ── Local form state for non-list config fields ─────────────────────
  const [formEnabled, setFormEnabled] = useState(liveConfig?.enabled ?? true);
  const [formThreshold, setFormThreshold] = useState(
    liveConfig?.player_threshold ?? 50
  );
  const [formHourStart, setFormHourStart] = useState(
    liveConfig?.seeding_hour_start ?? 23
  );
  const [formHourEnd, setFormHourEnd] = useState(
    liveConfig?.seeding_hour_end ?? 6
  );
  useEffect(() => {
    if (liveConfig) {
      setFormEnabled(liveConfig.enabled);
      setFormThreshold(liveConfig.player_threshold);
      setFormHourStart(liveConfig.seeding_hour_start);
      setFormHourEnd(liveConfig.seeding_hour_end);
    }
  }, [liveConfig]);

  const isFormDirty =
    liveConfig &&
    (formEnabled !== liveConfig.enabled ||
      formThreshold !== liveConfig.player_threshold ||
      formHourStart !== liveConfig.seeding_hour_start ||
      formHourEnd !== liveConfig.seeding_hour_end);

  const handleSaveConfig = () => {
    saveConfig({
      enabled: formEnabled,
      player_threshold: Number(formThreshold),
      seeding_hour_start: Number(formHourStart),
      seeding_hour_end: Number(formHourEnd),
      // Lists preserved on the backend — we only send scalars here
      warfare_layer_ids: liveWhitelist?.warfare || [],
      offensive_layer_ids: liveWhitelist?.offensive || [],
    });
  };

  const isAnyPending =
    isSavingWarfare || isSavingOffensive || isResetting || isSavingConfig;

  // Sub-tab between warfare and offensive pickers — only one visible
  // at a time so each picker has full width and isn't lost below a long
  // scroll. Default to warfare (the bigger list, what admins edit more).
  const [listTab, setListTab] = useState(0);

  return (
    <Stack spacing={2} sx={{ position: "relative" }}>
      {isAnyPending && (
        <LinearProgress
          sx={{ position: "absolute", top: 0, left: 0, right: 0, height: "2px" }}
        />
      )}

      <Alert severity="info">
        These maps and settings only apply during the seeding window —
        when the player count is below the threshold OR the Kyiv local hour
        falls in the configured range. Outside the seeding window, the regular
        Map Whitelist tab applies.
      </Alert>

      {/* ── Settings panel ────────────────────────────────────────── */}
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Seeding window settings
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems="center">
          <FormControlLabel
            control={
              <Switch
                checked={formEnabled}
                onChange={(e) => setFormEnabled(e.target.checked)}
              />
            }
            label="Enabled"
          />
          <TextField
            label="Player threshold"
            type="number"
            size="small"
            inputProps={{ min: 0, max: 100 }}
            value={formThreshold}
            onChange={(e) => setFormThreshold(e.target.value)}
            helperText="Below this many players → seeding"
          />
          <TextField
            label="Hour start (Kyiv)"
            type="number"
            size="small"
            inputProps={{ min: 0, max: 23 }}
            value={formHourStart}
            onChange={(e) => setFormHourStart(e.target.value)}
          />
          <TextField
            label="Hour end (Kyiv)"
            type="number"
            size="small"
            inputProps={{ min: 0, max: 23 }}
            value={formHourEnd}
            onChange={(e) => setFormHourEnd(e.target.value)}
            helperText={`Window: ${formHourStart}:00 – ${formHourEnd}:00 (wraps midnight if start > end)`}
          />
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            disabled={!isFormDirty || isSavingConfig}
            onClick={handleSaveConfig}
          >
            Save settings
          </Button>
        </Stack>
      </Paper>

      <Divider />

      {/* ── Sub-tabs: Warfare ↔ Offensive ─────────────────────────── */}
      {/* Only one list visible at a time — each picker gets full width
          (filter sidebar + available pool + selected list), and switching
          is one click instead of a long scroll. */}
      <Paper sx={{ p: 0 }}>
        <Box sx={{ borderBottom: 1, borderColor: "divider", px: 2 }}>
          <Tabs
            value={listTab}
            onChange={(_, v) => setListTab(v)}
            aria-label="seeding list type"
          >
            <Tab
              label={
                <Stack direction="row" spacing={1} alignItems="center">
                  <span>Warfare</span>
                  <Chip
                    size="small"
                    label={selectedWarfare.length}
                    color={listTab === 0 ? "primary" : "default"}
                  />
                </Stack>
              }
            />
            <Tab
              label={
                <Stack direction="row" spacing={1} alignItems="center">
                  <span>Offensive</span>
                  <Chip
                    size="small"
                    label={selectedOffensive.length}
                    color={listTab === 1 ? "primary" : "default"}
                  />
                </Stack>
              }
            />
            <Box sx={{ flexGrow: 1 }} />
            <Box sx={{ display: "flex", alignItems: "center" }}>
              <Tooltip title="Reset both warfare + offensive lists to the curated 7+7 defaults">
                <IconButton
                  onClick={() => resetWhitelist()}
                  size="small"
                  color="warning"
                >
                  <RestoreIcon />
                </IconButton>
              </Tooltip>
            </Box>
          </Tabs>
        </Box>

        <Box sx={{ p: 2 }}>
          {listTab === 0 && (
            <Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Warfare layers available during seeding. Votemap picks{" "}
                <b>num_warfare_options</b> (see Settings tab) random items
                from this list.
              </Typography>
              <MapListBuilder
                key="warfare"
                maps={warfareMaps}
                selectedMaps={selectedWarfare}
                onSave={(ids) => saveWarfare(ids)}
                isSaving={isSavingWarfare}
                isSaveDisabled={isSavingWarfare}
                exclusive={true}
                slots={{
                  SelectedMapList: MapWhitelistList,
                  MapListItem: MapBuilderListItem,
                }}
              />
            </Box>
          )}

          {listTab === 1 && (
            <Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Offensive layers available during seeding. Votemap picks{" "}
                <b>num_offensive_options</b> from this list. The dedup
                wrapper ensures the chosen offensive's base map won't
                duplicate any warfare slot in the same vote.
              </Typography>
              <MapListBuilder
                key="offensive"
                maps={offensiveMaps}
                selectedMaps={selectedOffensive}
                onSave={(ids) => saveOffensive(ids)}
                isSaving={isSavingOffensive}
                isSaveDisabled={isSavingOffensive}
                exclusive={true}
                slots={{
                  SelectedMapList: MapWhitelistList,
                  MapListItem: MapBuilderListItem,
                }}
              />
            </Box>
          )}
        </Box>
      </Paper>
    </Stack>
  );
}

export default VotemapSeedingPage;
