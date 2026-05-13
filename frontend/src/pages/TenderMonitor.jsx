import { useEffect, useMemo, useState } from 'react';
import {
  createOpportunity,
  deleteOpportunity,
  getApiUrl,
  listOpportunities,
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

function normalizeFormPayload(form) {
  return Object.fromEntries(
    Object.entries(form).map(([key, value]) => [key, typeof value === 'string' ? value.trim() : value])
  );
}

function formatDate(value) {
  if (!value) return '—';
  try {
    return new Intl.DateTimeFormat('fa-IR').format(new Date(value));
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

export default function TenderMonitor() {
  const [opportunities, setOpportunities] = useState([]);
  const [searchRules, setSearchRules] = useState([]);
  const [form, setForm] = useState(defaultForm);
  const [filters, setFilters] = useState({
    search: '',
    status: '',
    opportunity_type: '',
    region_priority: '',
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  async function loadData(activeFilters = filters) {
    setLoading(true);
    setError('');
    try {
      const [opportunityData, ruleData] = await Promise.all([
        listOpportunities(activeFilters),
        listSearchRules().catch(() => []),
      ]);
      setOpportunities(opportunityData);
      setSearchRules(ruleData);
    } catch (err) {
      setError('خطا در دریافت اطلاعات. لطفاً اتصال به API و Supabase را بررسی کنید.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  function updateFilter(field, value) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setError('');
    setSuccessMessage('');

    try {
      const payload = normalizeFormPayload(form);
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
      <section className="hero-card">
        <div>
          <p className="eyebrow">Niroban Rev 1A</p>
          <h1>نیروبان</h1>
          <p className="hero-subtitle">
            داشبورد فارسی پایش مناقصات، استعلام قیمت و استعلام‌های مرتبط با تجهیزات برق برای گسترش انرژی.
          </p>
        </div>
        <div className="api-pill">
          <span>API</span>
          <strong>{getApiUrl()}</strong>
        </div>
      </section>

      {(error || successMessage) && (
        <section className={error ? 'message message-error' : 'message message-success'}>
          {error || successMessage}
        </section>
      )}

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

      <section className="content-grid">
        <article className="panel form-panel">
          <div className="panel-header">
            <div>
              <h2>ثبت فرصت جدید</h2>
              <p>در Rev 1A فرصت‌ها به‌صورت دستی وارد می‌شوند.</p>
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

        <article className="panel rules-panel">
          <div className="panel-header">
            <div>
              <h2>کلمات کلیدی فعال</h2>
              <p>این کلمات در Rev 1B برای پایش خودکار استفاده می‌شوند.</p>
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
