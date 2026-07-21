import { useStore } from '../store';

const LANGUAGES = [
  { value: 'zh', label: '中文' },
  { value: 'en', label: 'English' },
  { value: 'ja', label: '日本語' },
  { value: 'ko', label: '한국어' },
  { value: 'de', label: 'Deutsch' },
  { value: 'fr', label: 'Français' },
];

const DIALECTS = [
  { value: '普通话', label: '普通话' },
  { value: '粤语', label: '粤语' },
  { value: '四川话', label: '四川话' },
  { value: '上海话', label: '上海话' },
  { value: '闽南语', label: '闽南语' },
  { value: '客家话', label: '客家话' },
];

export function LanguageDialectSelect() {
  const language = useStore(s => s.language);
  const dialect = useStore(s => s.dialect);
  const setInput = useStore(s => s.setInput);

  return (
    <div className="flex gap-4">
      <div className="flex-1 space-y-1">
        <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">语言</label>
        <select
          value={language}
          onChange={e => setInput('language', e.target.value)}
          className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-[15px] bg-gray-50/50 cursor-pointer focus:outline-none focus:border-violet-500 transition-colors appearance-none"
        >
          {LANGUAGES.map(l => (
            <option key={l.value} value={l.value}>{l.label}</option>
          ))}
        </select>
      </div>
      <div className="flex-1 space-y-1">
        <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
          方言 <span className="font-normal normal-case text-gray-300">— 可选</span>
        </label>
        <select
          value={dialect}
          onChange={e => setInput('dialect', e.target.value)}
          className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-[15px] bg-gray-50/50 cursor-pointer focus:outline-none focus:border-violet-500 transition-colors appearance-none"
        >
          {DIALECTS.map(d => (
            <option key={d.value} value={d.value}>{d.label}</option>
          ))}
        </select>
      </div>
    </div>
  );
}
