# uipath.cryptography.activities
Assembly: UiPath.Cryptography.Activities v1.4.2.0
PackageVersion: 1.4.2
ActivityCount: 8

## UiPath.Cryptography.Activities.DecryptFile
- required:
  - **Algorithm** : UiPath.Cryptography.SymmetricAlgorithms [Plain]  // Algoritmo
  - **Overwrite** : Boolean [Plain]  // Substituir
  - **InputFile** : UiPath.Platform.ResourceHandling.IResource [In]  @group=InputFile  // Arquivo
- optional:
  - InputFilePath : String [In]  @group=InputFilePath  // Caminho de Entrada
  - Key : String [In]  // Chave
  - KeyInputModeSwitch : UiPath.Cryptography.Enums.KeyInputMode [Plain]  // AlterarModoDeEntradaDaChave
  - KeySecureString : Security.SecureString [In]  // String Segura da Chave
  - KeyEncoding : Text.Encoding [In]  // Codificação de Chave
  - KeyEncodingString : String [In]
  - FileInputModeSwitch : UiPath.Cryptography.Enums.FileInputMode [Plain]  // FileInputModeSwitch
  - OutputFilePath : String [In]  // Nome e local do arquivo de saída
  - OutputFileName : String [In]  // Nome de Arquivo Descriptografado
  - ContinueOnError : Boolean [In]  // Continuar com Erro
  - DecryptedFile : UiPath.Platform.ResourceHandling.ILocalResource [Out]  // Arquivo Descriptografado
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Cryptography.Activities.DecryptText
- required:
  - **Algorithm** : UiPath.Cryptography.SymmetricAlgorithms [Plain]  // Algoritmo
  - **Input** : String [In]  // Texto
- optional:
  - Key : String [In]  // Chave
  - KeyInputModeSwitch : UiPath.Cryptography.Enums.KeyInputMode [Plain]  // AlterarModoDeEntradaDaChave
  - KeySecureString : Security.SecureString [In]  // String Segura da Chave
  - Encoding : Text.Encoding [In]  // Codificação
  - KeyEncodingString : String [In]
  - Result : String [Out]  // Texto Descriptografado
  - ContinueOnError : Boolean [In]  // Continuar com Erro
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Cryptography.Activities.EncryptFile
- required:
  - **Algorithm** : UiPath.Cryptography.SymmetricAlgorithms [Plain]  // Algoritmo
  - **Overwrite** : Boolean [Plain]  // Substituir
  - **InputFile** : UiPath.Platform.ResourceHandling.IResource [In]  @group=InputFile  // Arquivo
- optional:
  - InputFilePath : String [In]  @group=InputFilePath  // Caminho de Entrada
  - Key : String [In]  // Chave
  - FileInputModeSwitch : UiPath.Cryptography.Enums.FileInputMode [Plain]  // FileInputModeSwitch
  - KeyInputModeSwitch : UiPath.Cryptography.Enums.KeyInputMode [Plain]  // AlterarModoDeEntradaDaChave
  - KeySecureString : Security.SecureString [In]  // String Segura da Chave
  - KeyEncoding : Text.Encoding [In]  // Codificação de Chave
  - KeyEncodingString : String [In]
  - OutputFilePath : String [In]  // Nome e local do arquivo de saída
  - OutputFileName : String [In]  // Nome de Arquivo Criptografado
  - ContinueOnError : Boolean [In]  // Continuar com Erro
  - EncryptedFile : UiPath.Platform.ResourceHandling.ILocalResource [Out]  // Arquivo Criptografado
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Cryptography.Activities.EncryptText
- required:
  - **Algorithm** : UiPath.Cryptography.SymmetricAlgorithms [Plain]  // Algoritmo
  - **Input** : String [In]  // Texto
- optional:
  - Key : String [In]  // Chave
  - KeyInputModeSwitch : UiPath.Cryptography.Enums.KeyInputMode [Plain]  // AlterarModoDeEntradaDaChave
  - KeySecureString : Security.SecureString [In]  // String Segura da Chave
  - Encoding : Text.Encoding [In]  // Codificação
  - KeyEncodingString : String [In]
  - Result : String [Out]  // Texto Criptografado
  - ContinueOnError : Boolean [In]  // Continuar com Erro
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Cryptography.Activities.HashFile
- required:
  - **Algorithm** : UiPath.Cryptography.KeyedHashAlgorithms [Plain]  // Algoritmo
  - **FilePath** : String [In]  @group=FilePath  // Caminho do arquivo
  - **InputFile** : UiPath.Platform.ResourceHandling.IResource [In]  @group=InputFile  // Arquivo
- optional:
  - Key : String [In]  // Chave
  - KeyInputModeSwitch : UiPath.Cryptography.Enums.KeyInputMode [Plain]  // Chave
  - KeySecureString : Security.SecureString [In]  // String Segura da Chave
  - Encoding : Text.Encoding [In]  // Codificação
  - KeyEncodingString : String [In]
  - Result : String [Out]  // Hash
  - ContinueOnError : Boolean [In]  // Continuar com Erro
  - FileInputModeSwitch : UiPath.Cryptography.Enums.FileInputMode [Plain]  // FileInputModeSwitch
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Cryptography.Activities.HashText
- required:
  - **Algorithm** : UiPath.Cryptography.KeyedHashAlgorithms [Plain]  // Algoritmo
  - **Input** : String [In]  // Texto
- optional:
  - Key : String [In]  // Chave
  - KeyInputModeSwitch : UiPath.Cryptography.Enums.KeyInputMode [Plain]  // Chave
  - KeySecureString : Security.SecureString [In]  // String Segura da Chave
  - Encoding : Text.Encoding [In]  // Codificação
  - KeyEncodingString : String [In]
  - Result : String [Out]  // Hash
  - ContinueOnError : Boolean [In]  // Continuar com Erro
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Cryptography.Activities.KeyedHashFile
- required:
  - **Algorithm** : UiPath.Cryptography.KeyedHashAlgorithms [Plain]  // Algoritmo
  - **FilePath** : String [In]  @group=FilePath  // Caminho do arquivo
  - **InputFile** : UiPath.Platform.ResourceHandling.IResource [In]  @group=InputFile  // Arquivo
- optional:
  - Key : String [In]  // Chave
  - KeyInputModeSwitch : UiPath.Cryptography.Enums.KeyInputMode [Plain]  // Chave
  - KeySecureString : Security.SecureString [In]  // String Segura da Chave
  - Encoding : Text.Encoding [In]  // Codificação
  - KeyEncodingString : String [In]
  - Result : String [Out]  // Hash
  - ContinueOnError : Boolean [In]  // Continuar com Erro
  - FileInputModeSwitch : UiPath.Cryptography.Enums.FileInputMode [Plain]  // FileInputModeSwitch
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Cryptography.Activities.KeyedHashText
- required:
  - **Algorithm** : UiPath.Cryptography.KeyedHashAlgorithms [Plain]  // Algoritmo
  - **Input** : String [In]  // Texto
- optional:
  - Key : String [In]  // Chave
  - KeyInputModeSwitch : UiPath.Cryptography.Enums.KeyInputMode [Plain]  // Chave
  - KeySecureString : Security.SecureString [In]  // String Segura da Chave
  - Encoding : Text.Encoding [In]  // Codificação
  - KeyEncodingString : String [In]
  - Result : String [Out]  // Hash
  - ContinueOnError : Boolean [In]  // Continuar com Erro
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

