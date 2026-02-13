<template>
  <t-dialog
    :visible="visible"
    header="Configuration"
    width="760px"
    :confirm-on-enter="false"
    @update:visible="handleVisibleChange"
  >
    <t-loading :loading="loading">
      <t-form label-align="left" label-width="180px">
        <t-form-item label="Auth Mode">
          <t-select v-model="form.openai_auth_mode" :options="authModeOptions" />
        </t-form-item>
        <t-form-item v-if="form.openai_auth_mode === 'api_key'" label="OpenAI API Key">
          <t-input v-model="form.openai_api_key" type="password" placeholder="sk-..." />
        </t-form-item>
        <template v-else>
          <t-form-item label="Codex OAuth">
            <div class="codex-row">
              <t-button :loading="codexLoading" @click="loginCodex">Login</t-button>
              <t-button :loading="codexLoading" variant="outline" @click="refreshCodex">Refresh</t-button>
            </div>
          </t-form-item>
          <t-form-item label="Codex Account">
            <t-input :value="form.codex_account_id || 'Not logged in'" readonly />
          </t-form-item>
          <t-form-item label="Codex Expires">
            <t-input :value="formatExpiresAt(form.codex_expires_at)" readonly />
          </t-form-item>
        </template>
        <t-form-item label="OpenAI Model">
          <t-input v-model="form.openai_model" />
        </t-form-item>
        <t-form-item label="Enable Thinking">
          <t-switch v-model="form.enable_thinking" />
        </t-form-item>
        <t-form-item label="Shell Type">
          <t-select v-model="form.shell_type" :options="shellTypeOptions" />
        </t-form-item>
        <t-form-item label="Bash Path">
          <t-input v-model="form.bash_path" />
        </t-form-item>
        <t-form-item label="Tool History Rounds">
          <t-input-number v-model="form.tool_history_rounds" :min="0" />
        </t-form-item>
        <t-form-item label="CORS Origins">
          <t-textarea
            v-model="form.cors_origins_text"
            :autosize="{ minRows: 2, maxRows: 4 }"
            placeholder="One URL per line, or comma separated"
          />
        </t-form-item>
        <t-form-item label="Debug Mode">
          <t-switch v-model="form.debug" />
        </t-form-item>
      </t-form>
    </t-loading>
    <template #footer>
      <div class="config-footer">
        <t-button variant="outline" @click="handleVisibleChange(false)">Cancel</t-button>
        <t-button theme="primary" :loading="saving" @click="saveConfig">Save</t-button>
      </div>
    </template>
  </t-dialog>
</template>

<script setup>
import { ref, watch } from "vue";
import { MessagePlugin } from "tdesign-vue-next";

const API_BASE = "/api";
const OPENAI_BASE_URL_DEFAULT = "https://api.openai.com/v1";

const props = defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
});

const emits = defineEmits(["update:visible"]);

const loading = ref(false);
const saving = ref(false);
const codexLoading = ref(false);
const form = ref({
  openai_auth_mode: "api_key",
  openai_api_key: "",
  openai_model: "gpt-4-vision-preview",
  openai_base_url: "",
  codex_access_token: "",
  codex_refresh_token: "",
  codex_account_id: "",
  codex_expires_at: 0,
  debug: false,
  bash_path: "bash",
  shell_type: "auto",
  tool_history_rounds: 10,
  enable_thinking: false,
  cors_origins_text: "",
});

const shellTypeOptions = [
  { label: "auto", value: "auto" },
  { label: "bash", value: "bash" },
  { label: "cmd", value: "cmd" },
];
const authModeOptions = [
  { label: "api_key", value: "api_key" },
  { label: "codex", value: "codex" },
];

function handleVisibleChange(nextVisible) {
  emits("update:visible", nextVisible);
}

function parseCorsOrigins(text) {
  return text
    .split(/[\n,]/g)
    .map((v) => v.trim())
    .filter(Boolean);
}

async function loadConfig() {
  loading.value = true;
  try {
    const response = await fetch(`${API_BASE}/config`);
    if (!response.ok) throw new Error("Failed to load configuration");
    const data = await response.json();
    form.value = {
      openai_auth_mode: data.openai_auth_mode || "api_key",
      openai_api_key: data.openai_api_key || "",
      openai_model: data.openai_model || "gpt-4-vision-preview",
      openai_base_url:
        data.openai_auth_mode === "api_key"
          ? OPENAI_BASE_URL_DEFAULT
          : (data.openai_base_url || ""),
      codex_access_token: data.codex_access_token || "",
      codex_refresh_token: data.codex_refresh_token || "",
      codex_account_id: data.codex_account_id || "",
      codex_expires_at: Number(data.codex_expires_at || 0),
      debug: Boolean(data.debug),
      bash_path: data.bash_path || "bash",
      shell_type: data.shell_type || "auto",
      tool_history_rounds: Number(data.tool_history_rounds ?? 10),
      enable_thinking: Boolean(data.enable_thinking),
      cors_origins_text: (data.cors_origins || []).join("\n"),
    };
  } catch (error) {
    MessagePlugin.error(`Failed to load configuration: ${error.message}`);
  } finally {
    loading.value = false;
  }
}

async function saveConfig() {
  saving.value = true;
  try {
    const payload = {
      openai_auth_mode: form.value.openai_auth_mode || "api_key",
      openai_api_key: form.value.openai_api_key || "",
      openai_model: form.value.openai_model || "gpt-4-vision-preview",
      openai_base_url: form.value.openai_base_url || null,
      codex_access_token: form.value.codex_access_token || "",
      codex_refresh_token: form.value.codex_refresh_token || "",
      codex_account_id: form.value.codex_account_id || "",
      codex_expires_at: Number(form.value.codex_expires_at || 0),
      debug: Boolean(form.value.debug),
      bash_path: form.value.bash_path || "bash",
      shell_type: form.value.shell_type || "auto",
      tool_history_rounds: Number(form.value.tool_history_rounds ?? 10),
      enable_thinking: Boolean(form.value.enable_thinking),
      cors_origins: parseCorsOrigins(form.value.cors_origins_text || ""),
    };

    const response = await fetch(`${API_BASE}/config`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error("Failed to save configuration");

    MessagePlugin.success("Configuration saved");
    handleVisibleChange(false);
  } catch (error) {
    MessagePlugin.error(`Failed to save configuration: ${error.message}`);
  } finally {
    saving.value = false;
  }
}

function formatExpiresAt(expiresAt) {
  if (!expiresAt) return "Unknown";
  const date = new Date(Number(expiresAt));
  if (Number.isNaN(date.getTime())) return "Invalid";
  return date.toLocaleString();
}

async function loginCodex() {
  codexLoading.value = true;
  try {
    const response = await fetch(`${API_BASE}/config/codex/login`, { method: "POST" });
    if (!response.ok) throw new Error("Codex login failed");
    const data = await response.json();
    form.value = {
      ...form.value,
      openai_auth_mode: data.openai_auth_mode || "codex",
      codex_access_token: data.codex_access_token || "",
      codex_refresh_token: data.codex_refresh_token || "",
      codex_account_id: data.codex_account_id || "",
      codex_expires_at: Number(data.codex_expires_at || 0),
    };
    MessagePlugin.success("Codex login success");
  } catch (error) {
    MessagePlugin.error(`Codex login failed: ${error.message}`);
  } finally {
    codexLoading.value = false;
  }
}

async function refreshCodex() {
  codexLoading.value = true;
  try {
    const response = await fetch(`${API_BASE}/config/codex/refresh`, { method: "POST" });
    if (!response.ok) throw new Error("Codex refresh failed");
    const data = await response.json();
    form.value = {
      ...form.value,
      codex_access_token: data.codex_access_token || "",
      codex_refresh_token: data.codex_refresh_token || "",
      codex_account_id: data.codex_account_id || "",
      codex_expires_at: Number(data.codex_expires_at || 0),
    };
    MessagePlugin.success("Codex token refreshed");
  } catch (error) {
    MessagePlugin.error(`Codex refresh failed: ${error.message}`);
  } finally {
    codexLoading.value = false;
  }
}

watch(
  () => props.visible,
  (nextVisible) => {
    if (nextVisible) {
      loadConfig();
    }
  },
);

watch(
  () => form.value.openai_auth_mode,
  (mode) => {
    if (mode === "api_key") {
      form.value.openai_base_url = OPENAI_BASE_URL_DEFAULT;
    }
  },
);
</script>

<style scoped lang="less">
.config-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.codex-row {
  display: flex;
  gap: 8px;
}
</style>
