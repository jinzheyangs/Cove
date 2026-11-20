/* 只在 Capacitor 原生壳里生效的那点事。
   浏览器里 import 这些插件是安全的：它们在 web 上是空实现。 */

import { Capacitor } from '@capacitor/core';
import { StatusBar, Style } from '@capacitor/status-bar';
import { Keyboard } from '@capacitor/keyboard';
import { Haptics, ImpactStyle } from '@capacitor/haptics';

export const isNative = Capacitor.isNativePlatform();

export async function initNative() {
  if (!isNative) return;
  try {
    // 浅色界面：状态栏文字要深色
    await StatusBar.setStyle({ style: Style.Dark });
    await StatusBar.setBackgroundColor({ color: '#FFFFFF' });
    await StatusBar.setOverlaysWebView({ overlay: true });
  } catch (_) { /* iOS 不支持 backgroundColor，忽略 */ }
  try {
    await Keyboard.setAccessoryBarVisible({ isVisible: false });
  } catch (_) { /* iOS only */ }
}

/** 底部导航的轻触反馈：网页里没有，原生里就是那一下「嗒」 */
export function tap() {
  if (!isNative) return;
  Haptics.impact({ style: ImpactStyle.Light }).catch(() => {});
}
