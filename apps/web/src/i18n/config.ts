export const locales = ['en', 'ru', 'de', 'zh', 'ja', 'ko', 'fr', 'es'] as const;
export type Locale = (typeof locales)[number];

export const localeNames: Record<Locale, string> = {
  en: 'English',
  ru: 'Русский',
  de: 'Deutsch',
  zh: '中文',
  ja: '日本語',
  ko: '한국어',
  fr: 'Français',
  es: 'Español',
};

export const defaultLocale: Locale = 'en';
