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
  const warfareMaps = useMemo(
    () => maps.filter((m) => /warfare/i.test(m.id)),
    [maps]
  );
  const offensiveMaps = useMemo(
    () =>
      maps.filter(
        (m) => /offensive/i.test(m.id) || /_off_/i.test(m.id)
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

      {/* ── Warfare list builder ──────────────────────────────────── */}
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Seeding warfare whitelist
          <Typography component="span" sx={{ ml: 1 }} color="text.secondary">
            ({selectedWarfare.length} selected)
          </Typography>
        </Typography>
        <MapListBuilder
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
          actions={
            <Tooltip title="Reset both lists to the curated 7+7 defaults">
              <IconButton onClick={() => resetWhitelist()} size="small" color="warning">
                <RestoreIcon />
              </IconButton>
            </Tooltip>
          }
        />
      </Paper>

      <Divider />

      {/* ── Offensive list builder ────────────────────────────────── */}
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Seeding offensive whitelist
          <Typography component="span" sx={{ ml: 1 }} color="text.secondary">
            ({selectedOffensive.length} selected)
          </Typography>
        </Typography>
        <Box sx={{ mb: 1 }}>
          <Typography variant="caption" color="text.secondary">
            The dedup wrapper guarantees the chosen offensive's base map
            won't duplicate any warfare slot in the same vote.
          </Typography>
        </Box>
        <MapListBuilder
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
      </Paper>
    </Stack>
  );
}

export default VotemapSeedingPage;
