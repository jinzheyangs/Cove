/* 全 App 只有一个玻璃引擎实例：整棵树里也只可能有一台手机。
   做成单例是为了让「谁都能调一下几何」——面板、导航、视图变更都不必层层透传 prop。 */

import { createEngine } from './engine.js';

export const engine = createEngine();
