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
  async deployToEnvVars(vendor, configId) {
    if (window.pywebview) return await window.pywebview.api.deploy_to_env_vars(vendor, configId);
    return { success: true, message: '环境变量已设置', set_vars: [], failed_vars: [] };
  },
  async getEnvVarsStatus(vendor) {
    if (window.pywebview) return await window.pywebview.api.env_vars_status(vendor);
    return {};
  },
  async checkVendorVersions() {
    if (window.pywebview) return await window.pywebview.api.check_vendor_versions();
    return {};
  },
  async getMinVersions() {
    if (window.pywebview) return await window.pywebview.api.get_min_versions();
    return {};
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
  stepGuide: $('#step-guide'),
};



// ── 渲染左侧厂家列表 ──────────────────

function renderVendorList() {
  console.log('[renderVendorList] 开始渲染, state.vendors:', state.vendors);
  const list = dom.vendorList;
  list.innerHTML = '';

  VENDOR_ORDER.forEach(vk => {
    const vendor = state.vendors[vk];
    console.log(`[renderVendorList] 检查 vendor ${vk}:`, vendor);
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
  console.log('[renderVendorList] 渲染完成, 列表子元素数:', list.children.length);
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
  // 更新步骤提示到第2步
  stepGuide.setStep(2);
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
  // 更新步骤提示到第3步
  stepGuide.setStep(3);
}

function startNewConfig(vendor) {
  state.selectedVendor = vendor;
  state.selectedConfigId = null;
  state.isNewConfig = true;

  resetEditor(vendor);
  showEditor(vendor, null);
  renderVendorList();
  renderConfigCards();
  // 新建配置时回到第2步
  stepGuide.setStep(2);
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

async function handleDeployEnvVars() {
  if (!state.selectedVendor || !state.selectedConfigId) {
    setStatus('请先选择一个配置', 'error');
    return;
  }

  // 确认对话框
  const vendor = state.selectedVendor;
  const config = state.vendors[vendor]?.configs?.find(c => c.id === state.selectedConfigId);
  if (!config) return;

  const message = `即将将配置「${config.name}」部署到系统环境变量。\n\n这将设置以下环境变量：\n${vendor === 'claude' ? '• ANTHROPIC_AUTH_TOKEN\n• ANTHROPIC_BASE_URL\n• ANTHROPIC_MODEL' : vendor === 'codex' ? '• OPENAI_API_KEY' : '相关环境变量'}\n\n适用于新电脑首次配置或配置不生效的情况。\n是否继续？`;

  if (!confirm(message)) return;

  try {
    setStatus('正在部署环境变量...', 'neutral');
    const result = await api.deployToEnvVars(vendor, state.selectedConfigId);

    if (result.success) {
      setStatus(result.message || '环境变量已部署，重启终端后生效', 'success');
      alert('环境变量部署成功！\n\n' +
        `已设置：${result.set_vars.join(', ')}\n\n` +
        '提示：请关闭当前终端并重新打开，环境变量才会生效。');
    } else {
      setStatus(result.message || '部署失败', 'error');
      if (result.failed_vars && result.failed_vars.length > 0) {
        alert('部分环境变量设置失败：\n' + result.failed_vars.join('\n') + '\n\n可能需要管理员权限。');
      }
    }
  } catch (e) {
    setStatus('部署失败: ' + e.message, 'error');
    alert('环境变量部署失败：' + e.message + '\n\n提示：\n1. 请以管理员权限运行此应用\n2. 或手动在系统环境变量中设置');
  }
}

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
  $('#btn-deploy-env').addEventListener('click', handleDeployEnvVars);
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

  // 版本警告弹窗
  $('#version-ok').addEventListener('click', () => {
    versionOverlay.hide();
  });
  document.getElementById('version-overlay').addEventListener('click', (e) => {
    if (e.target === document.getElementById('version-overlay')) {
      versionOverlay.hide();
    }
  });

  // 帮助按钮
  $('#btn-help').addEventListener('click', () => {
    guideOverlay.show();
  });

  // 引导弹窗
  $('#guide-ok').addEventListener('click', () => {
    const noShow = $('#guide-no-show').checked;
    if (noShow) {
      localStorage.setItem('codepivot_guide_shown', 'true');
    }
    guideOverlay.hide();
  });
  document.getElementById('guide-overlay').addEventListener('click', (e) => {
    if (e.target === document.getElementById('guide-overlay')) {
      guideOverlay.hide();
    }
  });
}

// ── 初始化 ──────────────────────────────

// 弹窗控制
const versionOverlay = {
  el: () => document.getElementById('version-overlay'),
  warningsEl: () => document.getElementById('version-warnings'),
  show() { this.el().classList.remove('hidden'); },
  hide() { this.el().classList.add('hidden'); }
};

const guideOverlay = {
  el: () => document.getElementById('guide-overlay'),
  show() { this.el().classList.remove('hidden'); },
  hide() { this.el().classList.add('hidden'); }
};

// 步骤提示控制
const stepGuide = {
  el: () => document.getElementById('step-guide'),
  show() { this.el().classList.remove('hidden'); },
  hide() { this.el().classList.add('hidden'); },
  setStep(step) {
    const items = this.el().querySelectorAll('.step-item');
    items.forEach((item, idx) => {
      const num = idx + 1;
      if (num < step) {
        item.classList.add('completed');
        item.classList.remove('active');
      } else if (num === step) {
        item.classList.add('active');
        item.classList.remove('completed');
      } else {
        item.classList.remove('active', 'completed');
      }
    });
  }
};

async function checkAndShowVersionWarnings() {
  try {
    const versions = await api.checkVendorVersions();
    const minVersions = await api.getMinVersions();
    const warnings = [];

    for (const [vendor, [isCompatible, version, message]] of Object.entries(versions)) {
      if (!isCompatible && version !== '未安装') {
        const vendorNames = {
          'claude': 'Claude Code',
          'codex': 'Codex CLI',
          'gemini': 'Gemini CLI',
          'opencode': 'OpenCode'
        };
        warnings.push({
          name: vendorNames[vendor],
          version: version,
          message: message,
          minVersion: minVersions[vendor] || '最新版'
        });
      }
    }

    if (warnings.length > 0) {
      setTimeout(() => {
        const container = versionOverlay.warningsEl();
        container.innerHTML = '';
        warnings.forEach(w => {
          const div = document.createElement('div');
          div.className = 'bg-lego-bg rounded p-3 border-l-4 border-lego-yellow';

          const title = document.createElement('div');
          title.className = 'font-semibold text-lego-text mb-1';
          title.textContent = '⚠️ ' + w.name;

          const msg = document.createElement('div');
          msg.className = 'text-lego-muted text-xs mb-1';
          msg.textContent = w.message;

          const ver = document.createElement('div');
          ver.className = 'text-lego-orange text-xs';
          ver.textContent = '推荐版本: ' + w.minVersion;

          div.appendChild(title);
          div.appendChild(msg);
          div.appendChild(ver);
          container.appendChild(div);
        });
        versionOverlay.show();
      }, 800);
    }
  } catch (e) {
    console.log('版本检测失败:', e);
  }
}

async function init() {
  bindEvents();
  setStatus('正在加载...', 'neutral');

  // 等待 PyWebView 就绪
  if (!window.pywebview) {
    await new Promise((resolve) => {
      window.addEventListener('pywebviewready', resolve);
      setTimeout(resolve, 3000);
    });
  }

  // 检查 API 是否可用
  if (!window.pywebview || !window.pywebview.api) {
    setStatus('API 未就绪', 'error');
    alert('错误：无法连接到后端 API\n\n请重新启动应用程序。');
    return;
  }

  try {
    state.vendors = await api.getVendors();
    
    // 验证数据
    if (!state.vendors || Object.keys(state.vendors).length === 0) {
      setStatus('无配置数据', 'error');
      return;
    }
    
    renderVendorList();
    setStatus('就绪', 'success');

    // 显示步骤提示
    if (dom.stepGuide) {
      stepGuide.show();
      stepGuide.setStep(1);
    }
  } catch (e) {
    setStatus('加载失败: ' + e.message, 'error');
    alert('加载失败: ' + e.message);
  }
}

document.addEventListener('DOMContentLoaded', init);
