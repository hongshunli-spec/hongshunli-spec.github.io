import { printBanner } from './core/banner'
import { PublicAPI } from './core/public-api'

/**
 * FixIt theme entry point — initializes all modules and the window.fixit facade.
 *
 * Responsibilities:
 * - Create PublicAPI which initializes all service modules.
 * - Run the init sequence on `DOMContentLoaded`.
 */
function bootstrap(): void {
  // Build window.fixit facade with all modules
  window.fixit = new PublicAPI()

  /**
   * Initialize all modules in dependency order.
   *
   * 1. UI framework — menu (mask overlay), theme (color scheme)
   * 2. Interactive components — toc (sidebar), search (overlay)
   * 3. Content enhancement — content (details, tooltips), enc (decryption)
   * 4. Global features — misc (PWA, comments), events (scroll, resize)
   */
  function init() {
    // 各模块独立 try：某个模块失败不中断后续模块（修复 search.setup 偶发未执行）
    const safeSetup = (name: string) => {
      try {
        const svc = (window.fixit as any)[name] as { setup?: () => void } | undefined
        svc?.setup?.()
      }
      catch (err) {
        console.error(`[FixIt] ${name} setup failed:`, err)
      }
    }
    safeSetup('menu')
    safeSetup('theme')
    safeSetup('toc')
    safeSetup('search')
    safeSetup('content')
    safeSetup('enc')
    safeSetup('pwa')
    safeSetup('misc')
    safeSetup('events')
    printBanner(window.fixit.version)
  }

  document.addEventListener('DOMContentLoaded', init, false)
}

bootstrap()
