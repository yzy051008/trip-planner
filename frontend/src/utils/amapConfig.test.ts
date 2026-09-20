import { describe, expect, it } from 'vitest'
import { configureAmapSecurity, createAmapLoaderOptions } from './amapConfig'

describe('AMap loader configuration', () => {
  it('builds the JavaScript API loader options', () => {
    expect(createAmapLoaderOptions('js-key')).toEqual({
      key: 'js-key',
      version: '2.0',
      plugins: []
    })
  })

  it('configures the security code before loading the JavaScript API', () => {
    const target = {} as Record<string, unknown>

    configureAmapSecurity(target, 'security-code')

    expect(target._AMapSecurityConfig).toEqual({ securityJsCode: 'security-code' })
  })
})
