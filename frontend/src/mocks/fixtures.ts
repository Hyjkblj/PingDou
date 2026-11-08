import type { PaletteColor, Pattern, Project } from '../api/types';

export const mockColors: PaletteColor[] = [
  ['c01', 'H01', '纯白', '#f8f8f2'], ['c02', 'H02', '象牙白', '#eee9da'],
  ['c03', 'H03', '浅肤色', '#f2c39f'], ['c04', 'H04', '肤色', '#d99570'],
  ['c05', 'H05', '棕色', '#75462e'], ['c06', 'H06', '黑色', '#252525'],
  ['c07', 'H07', '灰色', '#8a9092'], ['c08', 'H08', '红色', '#d94b45'],
  ['c09', 'H09', '粉色', '#ef8eac'], ['c10', 'H10', '黄色', '#f0ce4d'],
  ['c11', 'H11', '绿色', '#489664'], ['c12', 'H12', '浅蓝', '#78b8df'],
  ['c13', 'H13', '蓝色', '#426bae'], ['c14', 'H14', '紫色', '#7f65a0'],
  ['c15', 'H15', '橙色', '#e87c3d'], ['c16', 'H16', '深绿', '#285b40'],
].map(([id, code, name, rgb]) => ({
  id, code, name, rgb, lab: [], attributes: ['OPAQUE'], enabled: true,
}));

const now = () => new Date().toISOString();

export const mockProjects: Project[] = [
  {
    id: 'project-demo-01',
    name: '小橘猫头像',
    status: 'EDITING',
    coverUrl: null,
    entitlementId: 'ent-demo-01',
    latestPatternId: 'pattern-demo-01',
    updatedAt: now(),
  },
  {
    id: 'project-demo-02',
    name: '山茶花杯垫',
    status: 'BASE_IMAGE_PENDING',
    coverUrl: null,
    entitlementId: 'ent-demo-02',
    latestPatternId: null,
    updatedAt: new Date(Date.now() - 86400000).toISOString(),
  },
];

function createMatrix(width: number, height: number): (string | null)[][] {
  const matrix: (string | null)[][] = [];
  const cx = width / 2;
  const cy = height / 2;
  for (let row = 0; row < height; row += 1) {
    const line: (string | null)[] = [];
    for (let column = 0; column < width; column += 1) {
      const x = (column - cx) / (width * 0.34);
      const y = (row - cy) / (height * 0.39);
      const face = x * x + y * y < 1;
      if (!face) { line.push(null); continue; }
      const ear = row < height * 0.26 && Math.abs(column - cx) > width * 0.16;
      const eye = row > height * 0.39 && row < height * 0.48 && Math.abs(Math.abs(column - cx) - width * 0.16) < width * 0.05;
      const nose = row > height * 0.51 && row < height * 0.59 && Math.abs(column - cx) < width * 0.07;
      const shadow = column < cx - width * 0.17 || row > height * 0.7;
      line.push(eye ? 'c06' : nose ? 'c09' : ear ? 'c15' : shadow ? 'c04' : 'c03');
    }
    matrix.push(line);
  }
  return matrix;
}

export function createMockPattern(id = 'pattern-demo-01', projectId = 'project-demo-01', width = 32, height = 32): Pattern {
  const matrix = createMatrix(width, height);
  return {
    id,
    projectId,
    version: 1,
    width,
    height,
    beadSizeMm: 5,
    backgroundMode: 'WHITE_PREVIEW',
    matrix,
    lockedCells: [],
    palette: { id: 'palette-pingdou', version: 'PINGDOU-2026.1', colors: mockColors },
    params: { maxColors: 16, optimizationTarget: 'BALANCED' },
    score: {
      total: 86,
      recognizability: 91,
      outlineIntegrity: 88,
      colorEconomy: 83,
      connectivity: 82,
      estimatedManualEditCells: 18,
    },
    matrixChecksum: 'mock-checksum-1',
  };
}

export const mockPatterns = new Map<string, Pattern>([
  ['pattern-demo-01', createMockPattern()],
]);
