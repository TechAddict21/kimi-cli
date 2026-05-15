# ConfigApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**getConfigTomlApiConfigTomlGet**](ConfigApi.md#getconfigtomlapiconfigtomlget) | **GET** /api/config/toml | Get pc-kimi-cli config.toml |
| [**getGlobalConfigApiConfigGet**](ConfigApi.md#getglobalconfigapiconfigget) | **GET** /api/config/ | Get global (pc-kimi-cli) config snapshot |
| [**updateConfigTomlApiConfigTomlPut**](ConfigApi.md#updateconfigtomlapiconfigtomlput) | **PUT** /api/config/toml | Update pc-kimi-cli config.toml |
| [**updateGlobalConfigApiConfigPatch**](ConfigApi.md#updateglobalconfigapiconfigpatch) | **PATCH** /api/config/ | Update global (pc-kimi-cli) default model/thinking |



## getConfigTomlApiConfigTomlGet

> ConfigToml getConfigTomlApiConfigTomlGet()

Get pc-kimi-cli config.toml

Get pc-kimi-cli config.toml.

### Example

```ts
import {
  Configuration,
  ConfigApi,
} from '';
import type { GetConfigTomlApiConfigTomlGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new ConfigApi();

  try {
    const data = await api.getConfigTomlApiConfigTomlGet();
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

This endpoint does not need any parameter.

### Return type

[**ConfigToml**](ConfigToml.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getGlobalConfigApiConfigGet

> GlobalConfig getGlobalConfigApiConfigGet()

Get global (pc-kimi-cli) config snapshot

Get global (pc-kimi-cli) config snapshot.

### Example

```ts
import {
  Configuration,
  ConfigApi,
} from '';
import type { GetGlobalConfigApiConfigGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new ConfigApi();

  try {
    const data = await api.getGlobalConfigApiConfigGet();
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

This endpoint does not need any parameter.

### Return type

[**GlobalConfig**](GlobalConfig.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## updateConfigTomlApiConfigTomlPut

> UpdateConfigTomlResponse updateConfigTomlApiConfigTomlPut(updateConfigTomlRequest)

Update pc-kimi-cli config.toml

Update pc-kimi-cli config.toml.

### Example

```ts
import {
  Configuration,
  ConfigApi,
} from '';
import type { UpdateConfigTomlApiConfigTomlPutRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new ConfigApi();

  const body = {
    // UpdateConfigTomlRequest
    updateConfigTomlRequest: ...,
  } satisfies UpdateConfigTomlApiConfigTomlPutRequest;

  try {
    const data = await api.updateConfigTomlApiConfigTomlPut(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **updateConfigTomlRequest** | [UpdateConfigTomlRequest](UpdateConfigTomlRequest.md) |  | |

### Return type

[**UpdateConfigTomlResponse**](UpdateConfigTomlResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## updateGlobalConfigApiConfigPatch

> UpdateGlobalConfigResponse updateGlobalConfigApiConfigPatch(updateGlobalConfigRequest)

Update global (pc-kimi-cli) default model/thinking

Update global (pc-kimi-cli) default model/thinking.

### Example

```ts
import {
  Configuration,
  ConfigApi,
} from '';
import type { UpdateGlobalConfigApiConfigPatchRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new ConfigApi();

  const body = {
    // UpdateGlobalConfigRequest
    updateGlobalConfigRequest: ...,
  } satisfies UpdateGlobalConfigApiConfigPatchRequest;

  try {
    const data = await api.updateGlobalConfigApiConfigPatch(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **updateGlobalConfigRequest** | [UpdateGlobalConfigRequest](UpdateGlobalConfigRequest.md) |  | |

### Return type

[**UpdateGlobalConfigResponse**](UpdateGlobalConfigResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

