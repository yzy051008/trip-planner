export interface AmapLoaderOptions {
  key: string
  version: '2.0'
  plugins: string[]
}

export function createAmapLoaderOptions(
  key: string
): AmapLoaderOptions {
  return {
    key,
    version: '2.0',
    plugins: []
  }
}

export function configureAmapSecurity(
  target: Record<string, unknown>,
  securityJsCode: string
): void {
  if (securityJsCode) {
    target._AMapSecurityConfig = { securityJsCode }
  }
}
