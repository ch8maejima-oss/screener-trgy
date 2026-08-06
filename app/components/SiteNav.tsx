"use client";

import { useEffect, useRef, useState } from "react";
import { navItems, type NavItem } from "./nav-data";

/**
 * www.trgy.co.jp のグローバルナビゲーションを移植したプルダウンメニュー。
 * 項目名・リンク先は同一。全リンクは本ツールから離脱するため新規タブで開く。
 * 開閉はクリック操作に統一（ホバーのみに依存しない）し、タッチ・キーボード操作でも同等に使える。
 */

function isRealLink(href: string) {
  return href !== "#";
}

function NavLabel({ item }: { item: NavItem }) {
  if (!isRealLink(item.href)) {
    return <span className="site-nav__link site-nav__link--label">{item.label}</span>;
  }
  return (
    <a
      className="site-nav__link"
      href={item.href}
      target="_blank"
      rel="noopener noreferrer"
    >
      {item.label}
    </a>
  );
}

function NavBranch({ item, depth }: { item: NavItem; depth: number }) {
  const [open, setOpen] = useState(false);

  if (!item.children || item.children.length === 0) {
    return (
      <li className="site-nav__item" data-depth={depth}>
        <NavLabel item={item} />
      </li>
    );
  }

  return (
    <li
      className={`site-nav__item site-nav__item--parent ${open ? "is-open" : ""}`}
      data-depth={depth}
      onMouseEnter={depth === 0 ? () => setOpen(true) : undefined}
      onMouseLeave={depth === 0 ? () => setOpen(false) : undefined}
    >
      <span className="site-nav__row">
        <NavLabel item={item} />
        <button
          type="button"
          className="site-nav__caret"
          aria-expanded={open}
          aria-label={`${item.label}のサブメニューを${open ? "閉じる" : "開く"}`}
          onClick={() => setOpen((v) => !v)}
        >
          <svg viewBox="0 0 12 8" width="10" height="7" aria-hidden="true">
            <path d="M1 1l5 5 5-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </span>
      {open && (
        <ul className="site-nav__submenu" data-depth={depth + 1}>
          {item.children.map((child) => (
            <NavBranch key={child.label} item={child} depth={depth + 1} />
          ))}
        </ul>
      )}
    </li>
  );
}

export default function SiteNav() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const navRef = useRef<HTMLElement>(null);

  useEffect(() => {
    setMobileOpen(false);
  }, []);

  useEffect(() => {
    function handleKeydown(e: KeyboardEvent) {
      if (e.key === "Escape") setMobileOpen(false);
    }
    document.addEventListener("keydown", handleKeydown);
    return () => document.removeEventListener("keydown", handleKeydown);
  }, []);

  return (
    <nav className="site-nav" aria-label="メインメニュー" ref={navRef}>
      <button
        type="button"
        className="site-nav__toggle"
        aria-expanded={mobileOpen}
        aria-controls="site-nav-list"
        onClick={() => setMobileOpen((v) => !v)}
      >
        <span className="site-nav__toggle-bars" aria-hidden="true" />
        メニュー
      </button>
      <ul id="site-nav-list" className={`site-nav__list ${mobileOpen ? "is-open" : ""}`}>
        {navItems.map((item) => (
          <NavBranch key={item.label} item={item} depth={0} />
        ))}
      </ul>
    </nav>
  );
}
