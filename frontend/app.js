/* ═══════════════════════════════════════════
   AI 模型切换器 — 厂家优先前端逻辑
   ═══════════════════════════════════════════ */

const VENDOR_ORDER = ['claude', 'codex', 'gemini', 'opencode'];

// ── 状态 ──────────────────────────────────

let state = {
  vendors: {},           // {vendor_key: {display_name, subtitle, color, hint, configs[], current_config_id}}
  selectedVendor: null,  // 当前选中的厂家 key
  selectedConfigId: null, // 当前选中的配置 id
  isNewConfig: false,    // 是否正在新建
};
let pendingDelete = null; // {vendor, configId}

// ── API ──────────────────────────────────

const api = {
  async getVendors() {
    if (window.pywebview) return await window.pywebview.api.get_vendors();
    return state.vendors;
  },
  async saveVendorConfig(vendor, data) {
    if (window.pywebview) return await window.pywebview.api.save_vendor_config(vendor, data);
    if (!data.id) data.id = 'mock-' + Date.now();
    return data;
  },
  async deleteVendorConfig(vendor, configId) {
    if (window.pywebview) return await window.pywebview.api.delete_vendor_config(vendor, configId);
    return true;
  },
  async switchVendorConfig(vendor, configId) {
    if (window.pywebview) return await window.pywebview.api.switch_vendor_config(vendor, configId);
    return { success: true, message: '已切换', details: [] };
  },
};

// ── DOM ──────────────────────────────────

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const dom = {
  vendorList: $('#vendor-list'),
  configListArea: $('#config-list-area'),
  configListTitle: $('#config-list-title'),
  configCards: $('#config-cards'),
  modelHint: $('#model-hint'),
  editorEmpty: $('#editor-empty'),
  editorForm: $('#editor-form'),
  btnSwitch: $('#btn-switch'),
  btnDelete: $('#btn-delete'),
  statusDot: $('#status-dot'),
  statusText: $('#status-text'),
  confirmOverlay: $('#confirm-overlay'),
  confirmText: $('#confirm-text'),
  extraCodex: $('#extra-codex'),
  extraOpencode: $('#extra-opencode'),
};

// ── 渲染左侧厂家列表 ──────────────────

function renderVendorList() {
  const list = dom.vendorList;
  list.innerHTML = '';

  VENDOR_ORDER.forEach(vk => {
    const vendor = state.vendors[vk];
    if (!vendor) return;

    const item = document.createElement('div');
    item.className = `vendor-item ${vk === state.selectedVendor ? 'selected' : ''}`;
    item.dataset.vendor = vk;

    const count = (vendor.configs || []).length;
    const activeConfig = vendor.configs?.find(c => c.id === vendor.current_config_id);

    item.innerHTML = `
      <div class="vendor-dot" style="background:${vendor.color}"></div>
      <div class="vendor-item-info">
        <span class="vendor-item-name">${escapeHtml(vendor.display_name)}</span>
        <span class="vendor-item-sub">${escapeHtml(vendor.subtitle)}</span>
      </div>
      ${activeConfig ? '<span class="lego-badge-active" style="font-size:9px;padding:1px 4px;">' + escapeHtml(activeConfig.name) + '</span>' : (count > 0 ? '<span style="font-size:10px;color:var(--lego-muted)">' + count + '个</span>' : '')}
    `;
    list.appendChild(item);
  });
}

// ── 渲染右侧模型卡片 ─────────────────

function renderConfigCards() {
  const vk = state.selectedVendor;
  if (!vk) {
    dom.configListArea.classList.add('hidden');
    dom.editorEmpty.classList.remove('hidden');
    return;
  }

  const vendor = state.vendors[vk];
  dom.configListArea.classList.remove('hidden');
  dom.editorEmpty.classList.add('hidden');
  dom.configListTitle.textContent = `${vendor.display_name} 模型配置`;
  dom.modelHint.textContent = vendor.hint || '';

  const cards = dom.configCards;
  cards.innerHTML = '';

  const configs = vendor.configs || [];
  configs.forEach(cfg => {
    const isActive = cfg.id === vendor.current_config_id;
    const isSelected = cfg.id === state.selectedConfigId && !state.isNewConfig;

    const card = document.createElement('div');
    card.className = `config-card ${isSelected ? 'selected' : ''} ${isActive ? 'active' : ''}`;
    card.dataset.vendor = vk;
    card.dataset.id = cfg.id;

    let subtitle = '';
    if (cfg.api_url) {
      try { subtitle = new URL(cfg.api_url).hostname; } catch { subtitle = ''; }
    }
    if (cfg.model) subtitle += (subtitle ? ' · ' : '') + cfg.model;

    card.innerHTML = `
      <div class="config-card-info">
        <div class="config-card-name">${escapeHtml(cfg.name || '未命名')}</div>
        <div class="config-card-sub">${escapeHtml(subtitle)}</div>
      </div>
      ${isActive ? '<span class="lego-badge-active" style="font-size:9px;padding:1px 5px;">使用中</span>' : ''}
    `;
    cards.appendChild(card);
  });

  if (configs.length === 0) {
    cards.innerHTML = '<div style="color:var(--lego-muted);font-size:12px;padding:8px 0">暂无配置，点击“添加配置”创建</div>';
  }
}

function escapeHtml(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

// ── 状态栏 ──────────────────────────────

function setStatus(text, type = 'neutral') {
  dom.statusDot.className = 'lego-stud-sm ' + type;
  dom.statusText.textContent = text;
}

// ── 编辑器 ──────────────────────────────

function selectVendor(vk) {
  state.selectedVendor = vk;
  state.selectedConfigId = null;
  state.isNewConfig = false;
  hideEditor();
  renderVendorList();
  renderConfigCards();
}

function selectConfig(vendor, configId) {
  state.selectedVendor = vendor;
  state.selectedConfigId = configId;
  state.isNewConfig = false;

  const v = state.vendors[vendor];
  const cfg = v?.configs?.find(c => c.id === configId);
  if (!cfg) return;

  populateEditor(vendor, cfg);
  showEditor(vendor, cfg);
  renderVendorList();
  renderConfigCards();
}

function startNewConfig(vendor) {
  state.selectedVendor = vendor;
  state.selectedConfigId = null;
  state.isNewConfig = true;

  resetEditor(vendor);
  showEditor(vendor, null);
  renderVendorList();
  renderConfigCards();
}

function showEditor(vendor, cfg) {
  dom.editorForm.classList.remove('hidden');

  // 显示/隐藏厂家专属区域
  dom.extraCodex.classList.toggle('hidden', vendor !== 'codex');
  dom.extraOpencode.classList.toggle('hidden', vendor !== 'opencode');

  if (state.isNewConfig) {
    dom.btnSwitch.classList.add('hidden');
    dom.btnDelete.classList.add('hidden');
  } else {
    const v = state.vendors[vendor];
    const isActive = cfg?.id === v?.current_config_id;
    dom.btnSwitch.classList.toggle('hidden', isActive);
    dom.btnDelete.classList.remove('hidden');
  }
}

function hideEditor() {
  dom.editorForm.classList.add('hidden');
}

// ── 填充/重置 ────────────────────────────

function populateEditor(vendor, cfg) {
  $('#config-name').value = cfg.name || '';
  $('#cfg-api-url').value = cfg.api_url || '';
  $('#cfg-api-key').value = cfg.api_key || '';
  $('#cfg-model').value = cfg.model || '';

  if (vendor === 'codex') {
    $('#cfg-provider-name').value = cfg.provider_name || 'custom';
    $('#cfg-reasoning-effort').value = cfg.reasoning_effort || 'high';
  }
  if (vendor === 'opencode') {
    $('#cfg-provider-id').value = cfg.provider_id || '';
    $('#cfg-npm').value = cfg.npm || '';
    $('#cfg-display-name').value = cfg.display_name || '';
    $('#cfg-model-name').value = cfg.model_name || '';
    $('#cfg-context-limit').value = cfg.context_limit || 200000;
    $('#cfg-output-limit').value = cfg.output_limit || 64000;
  }
}

function resetEditor(vendor) {
  $('#config-name').value = '';
  $('#cfg-api-url').value = '';
  $('#cfg-api-key').value = '';
  $('#cfg-model').value = '';

  if (vendor === 'codex') {
    $('#cfg-provider-name').value = 'custom';
    $('#cfg-reasoning-effort').value = 'high';
  }
  if (vendor === 'opencode') {
    $('#cfg-provider-id').value = '';
    $('#cfg-npm').value = '';
    $('#cfg-display-name').value = '';
    $('#cfg-model-name').value = '';
    $('#cfg-context-limit').value = '200000';
    $('#cfg-output-limit').value = '64000';
  }
}

// ── 收集表单 ─────────────────────────────

function collectFormData() {
  const vendor = state.selectedVendor;
  const data = {};

  if (state.selectedConfigId && !state.isNewConfig) {
    data.id = state.selectedConfigId;
  }

  data.name = $('#config-name').value.trim() || '未命名';
  data.api_url = $('#cfg-api-url').value.trim();
  data.api_key = $('#cfg-api-key').value.trim();
  data.model = $('#cfg-model').value.trim();

  if (vendor === 'codex') {
    data.provider_name = $('#cfg-provider-name').value.trim() || 'custom';
    data.reasoning_effort = $('#cfg-reasoning-effort').value;
  }
  if (vendor === 'opencode') {
    data.provider_id = $('#cfg-provider-id').value.trim();
    data.npm = $('#cfg-npm').value.trim();
    data.display_name = $('#cfg-display-name').value.trim();
    data.model_name = $('#cfg-model-name').value.trim();
    data.context_limit = parseInt($('#cfg-context-limit').value) || 200000;
    data.output_limit = parseInt($('#cfg-output-limit').value) || 64000;
  }

  return data;
}

// ── 密钥显示/隐藏 ───────────────────────

function toggleKeyVisibility(targetId) {
  const input = $(`#${targetId}`);
  if (!input) return;
  input.type = input.type === 'password' ? 'text' : 'password';
}

// ── 操作 ────────────────────────────────

async function handleSwitch() {
  if (!state.selectedVendor || !state.selectedConfigId) return;
  setStatus('正在切换...', 'neutral');
  try {
    const result = await api.switchVendorConfig(state.selectedVendor, state.selectedConfigId);
    if (result.success) {
      state.vendors = await api.getVendors();
      renderVendorList();
      renderConfigCards();
      const v = state.vendors[state.selectedVendor];
      const cfg = v?.configs?.find(c => c.id === state.selectedConfigId);
      if (cfg) showEditor(state.selectedVendor, cfg);
      setStatus(result.message, 'success');
    } else {
      setStatus(result.message, 'error');
    }
  } catch (e) {
    setStatus('切换失败: ' + e.message, 'error');
  }
}

async function handleSave() {
  const vendor = state.selectedVendor;
  if (!vendor) return;
  const data = collectFormData();

  // 表单验证（Gemini 直连不需要 api_url）
  if (vendor !== 'gemini' && !data.api_url) {
    setStatus('请填写 API 地址', 'error');
    $('#cfg-api-url').focus();
    return;
  }
  if (!data.api_key) {
    setStatus('请填写 API 密钥', 'error');
    $('#cfg-api-key').focus();
    return;
  }

  try {
    const saved = await api.saveVendorConfig(vendor, data);
    state.vendors = await api.getVendors();
    state.selectedConfigId = saved.id;
    state.isNewConfig = false;
    renderVendorList();
    renderConfigCards();
    const v = state.vendors[vendor];
    const cfg = v?.configs?.find(c => c.id === saved.id);
    if (cfg) showEditor(vendor, cfg);
    setStatus(`配置「${saved.name || ''}」已保存`, 'success');
  } catch (e) {
    setStatus('保存失败: ' + e.message, 'error');
  }
}

function showDeleteConfirm(vendor, configId) {
  pendingDelete = { vendor, configId };
  const v = state.vendors[vendor];
  const cfg = v?.configs?.find(c => c.id === configId);
  dom.confirmText.textContent = `确定要删除「${cfg?.name || ''}」吗？此操作不可撤销。`;
  dom.confirmOverlay.classList.remove('hidden');
}

function hideDeleteConfirm() {
  dom.confirmOverlay.classList.add('hidden');
  pendingDelete = null;
}

async function confirmDelete() {
  if (!pendingDelete) return;
  const { vendor, configId } = pendingDelete;
  try {
    await api.deleteVendorConfig(vendor, configId);
    state.vendors = await api.getVendors();
    if (state.selectedVendor === vendor && state.selectedConfigId === configId) {
      state.selectedConfigId = null;
      state.isNewConfig = false;
      hideEditor();
    }
    hideDeleteConfirm();
    renderVendorList();
    renderConfigCards();
    setStatus('配置已删除', 'neutral');
  } catch (e) {
    setStatus('删除失败: ' + e.message, 'error');
  }
}

// ── 事件绑定 ────────────────────────────

function bindEvents() {
  $('#btn-save').addEventListener('click', handleSave);
  $('#btn-switch').addEventListener('click', handleSwitch);
  $('#btn-delete').addEventListener('click', () => {
    if (state.selectedVendor && state.selectedConfigId) {
      showDeleteConfirm(state.selectedVendor, state.selectedConfigId);
    }
  });

  // 密钥切换
  document.addEventListener('click', (e) => {
    const toggleBtn = e.target.closest('.key-toggle');
    if (toggleBtn) toggleKeyVisibility(toggleBtn.dataset.target);
  });

  // 厂家列表点击
  dom.vendorList.addEventListener('click', (e) => {
    const item = e.target.closest('.vendor-item');
    if (item) selectVendor(item.dataset.vendor);
  });

  // 模型卡片点击
  dom.configCards.addEventListener('click', (e) => {
    const card = e.target.closest('.config-card');
    if (card) selectConfig(card.dataset.vendor, card.dataset.id);
  });

  // 添加配置按钮
  $('#btn-add-config').addEventListener('click', () => {
    if (state.selectedVendor) startNewConfig(state.selectedVendor);
  });

  // 删除确认
  $('#confirm-ok').addEventListener('click', confirmDelete);
  $('#confirm-cancel').addEventListener('click', hideDeleteConfirm);
  dom.confirmOverlay.addEventListener('click', (e) => {
    if (e.target === dom.confirmOverlay) hideDeleteConfirm();
  });
}

// ── 初始化 ──────────────────────────────

async function init() {
  bindEvents();
  setStatus('正在加载...', 'neutral');

  if (!window.pywebview) {
    await new Promise((resolve) => {
      window.addEventListener('pywebviewready', resolve);
      setTimeout(resolve, 2000);
    });
  }

  try {
    state.vendors = await api.getVendors();
    renderVendorList();
    setStatus('就绪', 'success');
  } catch (e) {
    setStatus('加载失败: ' + e.message, 'error');
  }
}

document.addEventListener('DOMContentLoaded', init);
