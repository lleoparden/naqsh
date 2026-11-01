declare module "*.svg?raw" {
  const content: string;
  export default content;
}

interface ImportMetaEnv {
  readonly VITE_MASCOT?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
