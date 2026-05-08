# uipath.webapi.activities.runtime
Assembly: UiPath.Web.Activities v2.3.0.0
PackageVersion: 2.3.0
ActivityCount: 15

## UiPath.Web.Activities.DeserializeJson`1
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **JsonString** : String [In]  // String JSON
- optional:
  - JsonSample : String [Plain]  // Amostra de JSON
  - Settings : UiPath.Web.Activities.JSON.Models.JsonDeserializationSettings [In]  // Configurações do serializador
  - JsonObject : T [Out]  // ObjetoJSON
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Web.Activities.DeserializeJsonArray
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **JsonString** : String [In]  // String JSON
- optional:
  - JsonArray : Newtonsoft.Json.Linq.JArray [Out]  // Matriz JSON
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Web.Activities.DeserializeXml
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **XMLString** : String [In]  // StringXML
- optional:
  - XMLDocument : Xml.Linq.XDocument [Out]  // DocumentoXML
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Web.Activities.ExecuteXPath
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **ExistingXML** : Xml.Linq.XDocument [In]  @group=ExistingXML  // XML Existente
  - **XMLString** : String [In]  @group=XMLString  // StringXML
  - **XPathExpression** : String [In]  // Expressão XPath
- optional:
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Web.Activities.GetNodes
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **ExistingXML** : Xml.Linq.XDocument [In]  @group=Existing XML Document  // XML Existente
  - **XMLString** : String [In]  @group=XML Text  // StringXML
- optional:
  - XMLNodes : Collections.Generic.IEnumerable<Xml.Linq.XNode> [Out]  // NósXML
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Web.Activities.GetXMLNodeAttributes
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **ExistingXMLNode** : Xml.Linq.XNode [In]  // NóDoXmlExistente
- optional:
  - Attributes : Collections.Generic.IEnumerable<Xml.Linq.XAttribute> [Out]  // Atributos
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Web.Activities.GetXMLNodes
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **ExistingXML** : Xml.Linq.XDocument [In]  @group=Existing XML Document  // XML Existente
  - **XMLString** : String [In]  @group=XML Text  // StringXML
- optional:
  - XMLNodes : Collections.Generic.IEnumerable<Xml.Linq.XNode> [Out]  // NósXML
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Web.Activities.Http.NetHttpRequest
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **RequestUrl** : String [In]  // URL da Solicitação
- optional:
  - Method : UiPath.Web.Activities.Http.Models.HttpMethod [Plain]  // Método de Solicitação
  - Parameters : Collections.Generic.Dictionary<String,String> [In]  // Parâmetros
  - Headers : Collections.Generic.Dictionary<String,String> [In]  // Cabeçalhos
  - DisableSslVerification : Boolean [In]  // Desabilitar Verificação de SSL
  - TlsProtocol : UiPath.Web.Activities.Http.Models.SupportedTlsProtocols [In]  // Protocolo TLS
  - EnableCookies : Boolean [In]  // Habilitar cookies
  - ProxyConfiguration : UiPath.Web.Activities.Http.Models.WebProxyConfiguration [In]  // Proxy Configuration
  - ClientCertPath : String [In]  // Certificado do Cliente
  - ClientCertPassword : String [In]  // Senha do certificado do cliente
  - ClientCertSecurePassword : Security.SecureString [In]  // Senha segura do certificado do cliente
  - Cookies : Collections.Generic.Dictionary<String,String> [In]  // Cookies adicionais
  - TimeoutInMiliseconds : Nullable<Int32> [In]  // Tempo limite da solicitação
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - FollowRedirects : Boolean [In]  // Seguir redirecionamentos
  - MaxRedirects : Int32 [In]  // Máx. de redirecionamentos
  - AuthenticationType : UiPath.Web.Activities.Http.Models.AuthenticationType [Plain]  // Autenticação
  - BasicAuthUsername : String [In]  // Nome de Usuário
  - BasicAuthPassword : String [In]  // Senha
  - BasicAuthSecurePassword : Security.SecureString [In]  // Senha Segura
  - OAuthToken : String [In]  // Token de Portador
  - UseOsNegotiatedAuthCredentials : Boolean [In]  // Usar credenciais do sistema operacional
  - CustomNegotiatedAuthCredentials : Net.NetworkCredential [In]  // Credenciais personalizadas
  - RetryPolicyType : UiPath.Web.Activities.Http.Models.RetryPolicyType [Plain]  // Tipo de política de nova tentativa
  - RetryCount : Int32 [In]  // Número de novas tentativas
  - InitialDelay : Int32 [In]  // Atraso inicial
  - Multiplier : Double [In]  // Multiplicador
  - UseJitter : Boolean [In]  // Usar instabilidade
  - MaxRetryAfterDelay : Int32 [In]  // Limite de atraso
  - PreferRetryAfterValue : Boolean [In]  // Usar cabeçalho Retry-After
  - RetryStatusCodes : Collections.Generic.IEnumerable<Net.HttpStatusCode> [In]  // Códigos de status de nova tentativa
  - RequestBodyType : UiPath.Web.Activities.Http.Models.HttpRequestBodyType [Plain]  // Tipo de corpo da solicitação
  - FormData : Collections.Generic.Dictionary<String,String> [In]  // Dados de formulário codificados por URL
  - TextPayload : String [In]  // Carga do JSON
  - TextPayloadEncoding : String [In]  // Codificação de texto
  - TextPayloadContentType : String [In]  // Tipo de conteúdo do texto
  - BinaryPayload : Byte[] [In]  // Carga binária
  - FormDataParts : Collections.Generic.IEnumerable<UiPath.Web.Activities.Http.Models.FormDataPart> [In]  // Partes de dados do formulário
  - LocalFiles : Collections.Generic.IEnumerable<String> [In]  // Arquivos locais
  - ResourceFiles : Collections.Generic.IEnumerable<UiPath.Platform.ResourceHandling.IResource> [In]  // Arquivos de recurso
  - FilePath : String [In]  // Arquivo local
  - PathResource : UiPath.Platform.ResourceHandling.IResource [In]  // Arquivo de recurso
  - OutputFileName : String [In]  // NomeDoArquivoDeSaída
  - OutputFileTargetFolder : String [In]  // Pasta de destino do arquivo de saída
  - FileOverwrite : UiPath.Web.Activities.Http.Models.FileOverwriteOption [Plain]  // Se o arquivo já existir
  - SaveResponseAsFile : Boolean [In]  // Always save response as file
  - SaveRawRequestResponse : Boolean [In]  // Enable debugging info
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Web.Activities.HttpClient
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **EndPoint** : String [In]  // URL da Solicitação
- optional:
  - Method : UiPath.Web.Method [Plain]  // Método de Solicitação
  - AcceptFormat : UiPath.Web.AcceptHeaderType [Plain]  // Aceitar Formato
  - BodyFormat : String [Plain]  // Formato do Corpo
  - Body : String [In]  // Corpo
  - Headers : Collections.Generic.Dictionary<String,Activities.InArgument<String>> [Plain]  // Cabeçalhos
  - Cookies : Collections.Generic.Dictionary<String,Activities.InArgument<String>> [Plain]  // Cookies
  - Parameters : Collections.Generic.Dictionary<String,Activities.InArgument<String>> [Plain]  // Parâmetros
  - UrlSegments : Collections.Generic.Dictionary<String,Activities.InArgument<String>> [Plain]  // Segmentos de URL
  - Attachments : Collections.Generic.Dictionary<String,Activities.InArgument<String>> [Plain]  // Anexos
  - FileAttachments : Collections.Generic.ICollection<UiPath.Platform.ResourceHandling.ILocalResource> [In]  // Anexos de arquivo
  - ResourcePath : String [In]  // Nome de arquivo para anexo de resposta
  - Username : String [In]  @group=SimpleAuthentication  // Nome de Usuário
  - Password : String [In]  @group=SimpleAuthentication  // Senha
  - SecurePassword : Security.SecureString [In]  @group=SimpleAuthentication  // Senha Segura
  - ConsumerKey : String [In]  @group=OAuth1  // ChaveDoConsumidor
  - ConsumerSecret : String [In]  @group=OAuth1  // SegredoDoConsumidor
  - OAuth1Token : String [In]  @group=OAuth1  // TokenDoOAuth1
  - OAuth1TokenSecret : String [In]  @group=OAuth1  // SegredoDoTokenDoOAuth1
  - OAuth2Token : String [In]  @group=OAuth2  // TokenDoOAuth2
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - EnableSSLVerification : Boolean [In]  // Habilitar verificação de certificado SSL
  - ClientCertificate : String [In]  // CertificadoDoCliente
  - ClientCertificatePassword : String [In]  // SenhaDoCertificadoDoCliente
  - SecureClientCertificatePassword : Security.SecureString [In]  // SenhaSeguraDoCertificadoDoCliente
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - Result : String [Out]  // Conteúdo da resposta
  - StatusCode : Int32 [Out]  // Status da resposta
  - ResponseHeaders : Collections.Generic.Dictionary<String,String> [Out]  // Cabeçalhos
  - ResponseAttachment : UiPath.Platform.ResourceHandling.ILocalResource [Out]  // Anexo de resposta
  - AuthenticationType : UiPath.Web.Activities.HttpClient/AuthType [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Web.Activities.HttpSoapRequestServicePolicy
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - RuntimeServices : UiPath.Sdk.Activities.DependencyInjection.Contracts.IRuntimeServices [Plain]
  - Provider : IServiceProvider [Plain]

## UiPath.Web.Activities.JSON.SerializeJson
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **InputObject** : Object [In]  // Objeto de entrada
- optional:
  - Settings : UiPath.Web.Activities.JSON.Models.JsonSerializationSettings [In]  // Configurações do serializador
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Web.Activities.LocalizedCategoryAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Web.Activities.LocalizedDescriptionAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Description : String [Plain]

## UiPath.Web.Activities.LocalizedDisplayNameAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - DisplayName : String [Plain]

## UiPath.Web.Activities.SoapClient
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **ContractName** : String [In]  // Contrato de serviço
  - **EndPoint** : String [In]  // URL de solicitação SOAP
  - **Method** : String [In]  // Método SOAP
- optional:
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - Parameters : Collections.Generic.Dictionary<String,Activities.InArgument> [Plain]  // Parâmetros SOAP
  - Username : String [In]  @group=SimpleAuthentication  // Nome de Usuário
  - Password : String [In]  @group=SimpleAuthentication  // Senha
  - SecurePassword : Security.SecureString [In]  @group=SimpleAuthentication  // Senha Segura
  - UseWindowsCredentials : Boolean [Plain]  @group=WindowsAuthentication  // UsarCredenciaisDoWindows
  - ClientCertificate : String [In]  @group=ClientCertificateAuthentication  // Certificado do Cliente
  - ClientCertificatePassword : String [In]  // Senha do certificado do cliente
  - SecureClientCertificatePassword : Security.SecureString [In]  // Senha segura do certificado do cliente
  - ResponseHeaders : Collections.Generic.Dictionary<String,String> [Out]  // Cabeçalhos
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

