import { useEffect, useMemo, useState } from 'react';
import {
  createOpportunity,
  createScanLog,
  deleteOpportunity,
  getApiUrl,
  listOpportunities,
  listScanLogs,
  listSearchRules,
  updateOpportunity,
} from '../services/api.js';

const opportunityTypeLabels = {
  tender: 'مناقصه',
  price_inquiry: 'استعلام قیمت',
  inquiry: 'استعلام',
};

const statusLabels = {
  new: 'جدید',
  reviewed: 'بررسی شده',
  relevant: 'مرتبط',
  not_relevant: 'نامرتبط',
  applied: 'اقدام شده',
  missed: 'از دست رفته',
};

const regionLabels = {
  south: 'جنوب کشور',
  semnan: 'سمنان',
  other: 'سایر مناطق',
};

const scanStatusLabels = {
  pending: 'در انتظار بررسی',
  success: 'موفق',
  failed: 'ناموفق',
  login_required: 'نیازمند ورود دستی',
  captcha_required: 'نیازمند کپچا / تأیید دستی',
};

const scanModeLabels = {
  manual: 'دستی',
  semi_automatic: 'نیمه‌خودکار',
  automatic: 'خودکار',
};

const targetOpportunityTypes = ['مناقصه‌ها', 'استعلام قیمت', 'استعلام‌ها'];
const targetKeywords = ['رله', 'فیدر', 'پست برق', 'خازن', 'رله حفاظتی', 'بانک خازنی'];
const targetRegions = ['سراسر ایران', 'جنوب کشور', 'سمنان'];

const defaultForm = {
  title: '',
  opportunity_type: 'tender',
  company_name: '',
  province: '',
  region_priority: 'south',
  matched_keyword: 'رله',
  publish_date: '',
  deadline_date: '',
  source_url: '',
  notes: '',
  status: 'new',
};

const todayIso = () => new Date().toISOString().slice(0, 10);

const defaultScanForm = {
  scan_date: todayIso(),
  source_name: 'سامانه خصوصی مناقصات و استعلام‌ها',
  source_url: '',
  scan_mode: 'manual',
  status: 'success',
  total_found: 0,
  new_opportunities: 0,
  relevant_opportunities: 0,
  notes: '',
};

function normalizePayload(form) {
  return Object.fromEntries(
    Object.entries(form).map(([key, value]) => {
      if (typeof value === 'string') {
        return [key, value.trim()];
      }
      return [key, value];
    })
  );
}

function cleanEmptyValues(payload) {
  return Object.fromEntries(Object.entries(payload).filter(([, value]) => value !== '' && value !== null && value !== undefined));
}

function formatDate(value) {
  if (!value) return '—';
  try {
    return new Intl.DateTimeFormat('fa-IR').format(new Date(value));
  } catch {
    return value;
  }
}

function formatDateTime(value) {
  if (!value) return '—';
  try {
    return new Intl.DateTimeFormat('fa-IR', {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function isDeadlineSoon(deadlineDate) {
  if (!deadlineDate) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const deadline = new Date(deadlineDate);
  deadline.setHours(0, 0, 0, 0);

  const diffDays = Math.ceil((deadline - today) / (1000 * 60 * 60 * 24));
  return diffDays >= 0 && diffDays <= 7;
}

function getLastScanText(lastScan) {
  if (!lastScan) return 'هنوز ثبت نشده';
  return `${formatDate(lastScan.scan_date)} — ${scanStatusLabels[lastScan.status] || lastScan.status}`;
}

export default function TenderMonitor({ user, onSignOut }) {
  const [opportunities, setOpportunities] = useState([]);
  const [searchRules, setSearchRules] = useState([]);
  const [scanLogs, setScanLogs] = useState([]);
  const [form, setForm] = useState(defaultForm);
  const [scanForm, setScanForm] = useState(defaultScanForm);
  const [filters, setFilters] = useState({
    search: '',
    status: '',
    opportunity_type: '',
    region_priority: '',
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savingScan, setSavingScan] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  async function loadData(activeFilters = filters) {
    setLoading(true);
    setError('');
    try {
      const [opportunityData, ruleData, scanData] = await Promise.all([
        listOpportunities(activeFilters),
        listSearchRules().catch(() => []),
        listScanLogs(8).catch(() => []),
      ]);
      setOpportunities(opportunityData);
      setSearchRules(ruleData);
      setScanLogs(scanData);
    } catch (err) {
      setError('خطا در دریافت اطلاعات. لطفاً ورود، API، Supabase و جدول tender_scan_logs را بررسی کنید.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const lastScan = scanLogs[0];

  const summary = useMemo(() => {
    return {
      total: opportunities.length,
      newCount: opportunities.filter((item) => item.status === 'new').length,
      relevantCount: opportunities.filter((item) => item.status === 'relevant').length,
      deadlineSoonCount: opportunities.filter(
        (item) => !['applied', 'missed'].includes(item.status) && isDeadlineSoon(item.deadline_date)
      ).length,
      appliedCount: opportunities.filter((item) => item.status === 'applied').length,
    };
  }, [opportunities]);

  function updateForm(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function updateScanForm(field, value) {
    setScanForm((current) => ({ ...current, [field]: value }));
  }

  function updateFilter(field, value) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setError('');
    setSuccessMessage('');

    try {
      const payload = cleanEmptyValues(normalizePayload(form));
      if (!payload.title) {
        throw new Error('Title is required');
      }

      await createOpportunity(payload);
      setForm(defaultForm);
      setSuccessMessage('فرصت جدید با موفقیت ثبت شد.');
      await loadData();
    } catch (err) {
      setError('ثبت فرصت انجام نشد. لطفاً فیلدهای ضروری و اتصال backend را بررسی کنید.');
      console.error(err);
    } finally {
      setSaving(false);
    }
  }

  async function handleScanSubmit(event) {
    event.preventDefault();
    setSavingScan(true);
    setError('');
    setSuccessMessage('');

    try {
      const payload = cleanEmptyValues(normalizePayload(scanForm));
      payload.total_found = Number(payload.total_found || 0);
      payload.new_opportunities = Number(payload.new_opportunities || 0);
      payload.relevant_opportunities = Number(payload.relevant_opportunities || 0);
      payload.checked_opportunity_types = ['tender', 'price_inquiry', 'inquiry'];
      payload.checked_keywords = ['relay', 'feeder', 'substation', 'capacitor'];
      payload.checked_regions = ['south', 'semnan', 'all_iran'];

      await createScanLog(payload);
      setScanForm({ ...defaultScanForm, scan_date: todayIso() });
      setSuccessMessage('نتیجه پایش روزانه با موفقیت ثبت شد.');
      await loadData();
    } catch (err) {
      setError('ثبت گزارش پایش انجام نشد. جدول tender_scan_logs و اتصال backend را بررسی کنید.');
      console.error(err);
    } finally {
      setSavingScan(false);
    }
  }

  async function handleStatusChange(id, status) {
    setError('');
    try {
      const updated = await updateOpportunity(id, { status });
      setOpportunities((current) => current.map((item) => (item.id === id ? updated : item)));
    } catch (err) {
      setError('به‌روزرسانی وضعیت انجام نشد.');
      console.error(err);
    }
  }

  async function handleDelete(id) {
    const confirmed = window.confirm('آیا از حذف این فرصت مطمئن هستید؟');
    if (!confirmed) return;

    setError('');
    try {
      await deleteOpportunity(id);
      setOpportunities((current) => current.filter((item) => item.id !== id));
    } catch (err) {
      setError('حذف فرصت انجام نشد.');
      console.error(err);
    }
  }

  async function handleApplyFilters(event) {
    event.preventDefault();
    await loadData(filters);
  }

  async function handleResetFilters() {
    const resetFilters = {
      search: '',
      status: '',
      opportunity_type: '',
      region_priority: '',
    };
    setFilters(resetFilters);
    await loadData(resetFilters);
  }

  return (
    <main className="app-shell" dir="rtl">
      <section className="hero-card hero-card-rev1c">
        <div>
          <p className="eyebrow">Niroban Rev 1C</p>
          <h1>نیروبان</h1>
          <p className="hero-subtitle">
            سامانه پایش روزانه مناقصات و استعلام‌های صنعت برق برای گسترش انرژی. تمرکز این نسخه روی ثبت، کنترل و گزارش‌گیری
            فرآیند بررسی روزانه وب‌سایت خصوصی مناقصات است.
          </p>
        </div>
        <div className="hero-actions">
          <div className="user-pill">
            <span>کاربر وارد شده</span>
            <strong>{user?.email || '—'}</strong>
          </div>
          <div className="api-pill">
            <span>API</span>
            <strong>{getApiUrl()}</strong>
          </div>
          <button className="ghost-button logout-button" type="button" onClick={onSignOut}>
            خروج
          </button>
        </div>
      </section>

      {(error || successMessage) && (
        <section className={error ? 'message message-error' : 'message message-success'}>
          {error || successMessage}
        </section>
      )}

      <section className="monitoring-panel panel">
        <div className="panel-header monitoring-header">
          <div>
            <h2>پایش روزانه مناقصات و استعلام‌ها</h2>
            <p>
              وب‌سایت هدف عمومی نیست و ابتدا نیاز به ورود دارد. در Rev 1C نتیجه بررسی روزانه ثبت می‌شود؛ در Rev 1D اتصال
              نیمه‌خودکار به وب‌سایت با Playwright بررسی خواهد شد.
            </p>
          </div>
          <div className={`scan-status-badge scan-status-${lastScan?.status || 'pending'}`}>
            <span>آخرین پایش</span>
            <strong>{getLastScanText(lastScan)}</strong>
          </div>
        </div>

        <div className="target-grid">
          <article className="target-card">
            <span>نوع فرصت‌ها</span>
            <strong>{targetOpportunityTypes.join('، ')}</strong>
          </article>
          <article className="target-card">
            <span>کلمات کلیدی</span>
            <strong>{targetKeywords.join('، ')}</strong>
          </article>
          <article className="target-card">
            <span>محدوده بررسی</span>
            <strong>شرکت‌های برق منطقه‌ای و توزیع نیروی برق سراسر ایران، با اولویت جنوب کشور و سمنان</strong>
          </article>
        </div>
      </section>

      <section className="summary-grid">
        <article className="summary-card">
          <span>کل فرصت‌ها</span>
          <strong>{summary.total}</strong>
        </article>
        <article className="summary-card">
          <span>فرصت‌های جدید</span>
          <strong>{summary.newCount}</strong>
        </article>
        <article className="summary-card">
          <span>مرتبط</span>
          <strong>{summary.relevantCount}</strong>
        </article>
        <article className="summary-card warning">
          <span>مهلت نزدیک</span>
          <strong>{summary.deadlineSoonCount}</strong>
        </article>
        <article className="summary-card">
          <span>اقدام شده</span>
          <strong>{summary.appliedCount}</strong>
        </article>
      </section>

      <section className="content-grid rev1c-grid">
        <article className="panel form-panel">
          <div className="panel-header">
            <div>
              <h2>ثبت نتیجه پایش روزانه</h2>
              <p>پس از بررسی وب‌سایت خصوصی، نتیجه پایش امروز را اینجا ثبت کنید.</p>
            </div>
          </div>

          <form className="form-grid" onSubmit={handleScanSubmit}>
            <label>
              تاریخ پایش
              <input type="date" value={scanForm.scan_date} onChange={(event) => updateScanForm('scan_date', event.target.value)} />
            </label>

            <label>
              وضعیت پایش
              <select value={scanForm.status} onChange={(event) => updateScanForm('status', event.target.value)}>
                {Object.entries(scanStatusLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>

            <label>
              روش پایش
              <select value={scanForm.scan_mode} onChange={(event) => updateScanForm('scan_mode', event.target.value)}>
                {Object.entries(scanModeLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>

            <label>
              منبع بررسی‌شده
              <input
                value={scanForm.source_name}
                onChange={(event) => updateScanForm('source_name', event.target.value)}
                placeholder="سامانه خصوصی مناقصات"
              />
            </label>

            <label>
              کل موارد یافت‌شده
              <input
                type="number"
                min="0"
                value={scanForm.total_found}
                onChange={(event) => updateScanForm('total_found', event.target.value)}
              />
            </label>

            <label>
              فرصت‌های جدید
              <input
                type="number"
                min="0"
                value={scanForm.new_opportunities}
                onChange={(event) => updateScanForm('new_opportunities', event.target.value)}
              />
            </label>

            <label>
              فرصت‌های مرتبط
              <input
                type="number"
                min="0"
                value={scanForm.relevant_opportunities}
                onChange={(event) => updateScanForm('relevant_opportunities', event.target.value)}
              />
            </label>

            <label>
              لینک منبع
              <input
                value={scanForm.source_url}
                onChange={(event) => updateScanForm('source_url', event.target.value)}
                placeholder="https://..."
              />
            </label>

            <label className="full-width">
              یادداشت پایش
              <textarea
                value={scanForm.notes}
                onChange={(event) => updateScanForm('notes', event.target.value)}
                placeholder="مثلاً ورود موفق بود، کپچا وجود داشت، یا فرصت جدید مرتبط پیدا شد."
                rows="4"
              />
            </label>

            <button className="primary-button full-width" type="submit" disabled={savingScan}>
              {savingScan ? 'در حال ثبت...' : 'ثبت گزارش پایش امروز'}
            </button>
          </form>
        </article>

        <article className="panel rules-panel">
          <div className="panel-header">
            <div>
              <h2>کلمات کلیدی و مناطق هدف</h2>
              <p>این موارد معیار اصلی پایش روزانه هستند.</p>
            </div>
          </div>

          <div className="keyword-list">
            {searchRules.length === 0 ? (
              <span className="empty-state">هنوز کلمه کلیدی دریافت نشده است.</span>
            ) : (
              searchRules.map((rule) => (
                <span className="keyword-chip" key={rule.id}>
                  {rule.keyword_fa}
                  {rule.keyword_en ? <small>{rule.keyword_en}</small> : null}
                </span>
              ))
            )}
          </div>

          <div className="region-priority-box">
            <h3>اولویت جغرافیایی</h3>
            <ul>
              {targetRegions.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </article>
      </section>

      <section className="panel scan-log-panel">
        <div className="panel-header table-header">
          <div>
            <h2>گزارش پایش‌های اخیر</h2>
            <p>این بخش نشان می‌دهد که بررسی روزانه انجام شده یا نیازمند ورود/کپچا بوده است.</p>
          </div>
          <button className="secondary-button" onClick={() => loadData(filters)} disabled={loading}>
            {loading ? 'در حال دریافت...' : 'به‌روزرسانی'}
          </button>
        </div>

        <div className="scan-log-list">
          {scanLogs.length === 0 ? (
            <p className="empty-state">هنوز گزارشی برای پایش روزانه ثبت نشده است.</p>
          ) : (
            scanLogs.map((log) => (
              <article className="scan-log-item" key={log.id}>
                <div>
                  <strong>{formatDate(log.scan_date)}</strong>
                  <span>{log.source_name || 'سامانه خصوصی مناقصات'}</span>
                  {log.notes ? <p>{log.notes}</p> : null}
                </div>
                <div className="scan-log-metrics">
                  <span>{scanStatusLabels[log.status] || log.status}</span>
                  <small>کل: {log.total_found ?? 0}</small>
                  <small>جدید: {log.new_opportunities ?? 0}</small>
                  <small>مرتبط: {log.relevant_opportunities ?? 0}</small>
                  <small>ثبت: {formatDateTime(log.created_at)}</small>
                </div>
              </article>
            ))
          )}
        </div>
      </section>

      <section className="content-grid">
        <article className="panel form-panel">
          <div className="panel-header">
            <div>
              <h2>ثبت فرصت جدید</h2>
              <p>فرصت‌های پیدا شده در بررسی روزانه را اینجا ثبت کنید.</p>
            </div>
          </div>

          <form className="form-grid" onSubmit={handleSubmit}>
            <label className="full-width">
              عنوان فرصت *
              <input
                value={form.title}
                onChange={(event) => updateForm('title', event.target.value)}
                placeholder="مثلاً خرید رله حفاظتی برای پست برق"
                required
              />
            </label>

            <label>
              نوع فرصت
              <select
                value={form.opportunity_type}
                onChange={(event) => updateForm('opportunity_type', event.target.value)}
              >
                {Object.entries(opportunityTypeLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>

            <label>
              وضعیت
              <select value={form.status} onChange={(event) => updateForm('status', event.target.value)}>
                {Object.entries(statusLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>

            <label>
              شرکت اعلام‌کننده
              <input
                value={form.company_name}
                onChange={(event) => updateForm('company_name', event.target.value)}
                placeholder="مثلاً شرکت توزیع نیروی برق استان فارس"
              />
            </label>

            <label>
              استان
              <input
                value={form.province}
                onChange={(event) => updateForm('province', event.target.value)}
                placeholder="مثلاً فارس، سمنان، خوزستان"
              />
            </label>

            <label>
              منطقه هدف
              <select
                value={form.region_priority}
                onChange={(event) => updateForm('region_priority', event.target.value)}
              >
                {Object.entries(regionLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>

            <label>
              کلمه کلیدی
              <input
                value={form.matched_keyword}
                onChange={(event) => updateForm('matched_keyword', event.target.value)}
                list="keyword-options"
                placeholder="رله، فیدر، پست برق، خازن"
              />
              <datalist id="keyword-options">
                {searchRules.map((rule) => (
                  <option key={rule.id} value={rule.keyword_fa} />
                ))}
              </datalist>
            </label>

            <label>
              تاریخ انتشار
              <input
                type="date"
                value={form.publish_date}
                onChange={(event) => updateForm('publish_date', event.target.value)}
              />
            </label>

            <label>
              مهلت ارسال
              <input
                type="date"
                value={form.deadline_date}
                onChange={(event) => updateForm('deadline_date', event.target.value)}
              />
            </label>

            <label className="full-width">
              لینک منبع
              <input
                value={form.source_url}
                onChange={(event) => updateForm('source_url', event.target.value)}
                placeholder="https://..."
              />
            </label>

            <label className="full-width">
              یادداشت
              <textarea
                value={form.notes}
                onChange={(event) => updateForm('notes', event.target.value)}
                placeholder="توضیحات داخلی، نکات فنی یا نتیجه بررسی"
                rows="4"
              />
            </label>

            <button className="primary-button full-width" type="submit" disabled={saving}>
              {saving ? 'در حال ثبت...' : 'ثبت فرصت'}
            </button>
          </form>
        </article>

        <article className="panel guide-panel">
          <div className="panel-header">
            <div>
              <h2>چک‌لیست بررسی روزانه</h2>
              <p>این چک‌لیست فعلاً دستی است و در Rev 1D پایه اتصال نیمه‌خودکار خواهد شد.</p>
            </div>
          </div>
          <ol className="daily-checklist">
            <li>ورود به وب‌سایت خصوصی مناقصات با حساب مجاز.</li>
            <li>بررسی مناقصه‌ها، استعلام قیمت و استعلام‌ها.</li>
            <li>جستجوی کلمات رله، فیدر، پست برق و خازن.</li>
            <li>اولویت دادن به شرکت‌های برق منطقه‌ای و توزیع جنوب کشور و سمنان.</li>
            <li>ثبت فرصت‌های مرتبط و ثبت نتیجه پایش روزانه در نیروبان.</li>
          </ol>
        </article>
      </section>

      <section className="panel table-panel">
        <div className="panel-header table-header">
          <div>
            <h2>لیست فرصت‌ها</h2>
            <p>جستجو و فیلتر بر اساس نوع، وضعیت، منطقه و کلمه کلیدی.</p>
          </div>
          <button className="secondary-button" onClick={() => loadData(filters)} disabled={loading}>
            {loading ? 'در حال دریافت...' : 'به‌روزرسانی'}
          </button>
        </div>

        <form className="filters" onSubmit={handleApplyFilters}>
          <input
            value={filters.search}
            onChange={(event) => updateFilter('search', event.target.value)}
            placeholder="جستجو در عنوان، شرکت، استان یا کلمه کلیدی"
          />
          <select value={filters.opportunity_type} onChange={(event) => updateFilter('opportunity_type', event.target.value)}>
            <option value="">همه نوع‌ها</option>
            {Object.entries(opportunityTypeLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <select value={filters.status} onChange={(event) => updateFilter('status', event.target.value)}>
            <option value="">همه وضعیت‌ها</option>
            {Object.entries(statusLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <select value={filters.region_priority} onChange={(event) => updateFilter('region_priority', event.target.value)}>
            <option value="">همه مناطق</option>
            {Object.entries(regionLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <button className="primary-button" type="submit">
            اعمال فیلتر
          </button>
          <button className="ghost-button" type="button" onClick={handleResetFilters}>
            حذف فیلتر
          </button>
        </form>

        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>عنوان</th>
                <th>نوع</th>
                <th>شرکت</th>
                <th>استان</th>
                <th>منطقه</th>
                <th>کلمه کلیدی</th>
                <th>انتشار</th>
                <th>مهلت</th>
                <th>وضعیت</th>
                <th>عملیات</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="10" className="empty-table">
                    در حال دریافت اطلاعات...
                  </td>
                </tr>
              ) : opportunities.length === 0 ? (
                <tr>
                  <td colSpan="10" className="empty-table">
                    هنوز فرصتی ثبت نشده است.
                  </td>
                </tr>
              ) : (
                opportunities.map((item) => (
                  <tr key={item.id} className={isDeadlineSoon(item.deadline_date) ? 'deadline-soon-row' : ''}>
                    <td className="title-cell">
                      <strong>{item.title}</strong>
                      {item.source_url ? (
                        <a href={item.source_url} target="_blank" rel="noreferrer">
                          مشاهده منبع
                        </a>
                      ) : null}
                    </td>
                    <td>{opportunityTypeLabels[item.opportunity_type] || item.opportunity_type}</td>
                    <td>{item.company_name || '—'}</td>
                    <td>{item.province || '—'}</td>
                    <td>{regionLabels[item.region_priority] || '—'}</td>
                    <td>{item.matched_keyword || '—'}</td>
                    <td>{formatDate(item.publish_date)}</td>
                    <td>{formatDate(item.deadline_date)}</td>
                    <td>
                      <select
                        className="status-select"
                        value={item.status}
                        onChange={(event) => handleStatusChange(item.id, event.target.value)}
                      >
                        {Object.entries(statusLabels).map(([value, label]) => (
                          <option key={value} value={value}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <button className="danger-button" onClick={() => handleDelete(item.id)}>
                        حذف
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
