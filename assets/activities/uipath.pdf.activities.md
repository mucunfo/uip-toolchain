# uipath.pdf.activities
Assembly: UiPath.PDF.Activities v3.20.2.0
PackageVersion: 3.20.2
ActivityCount: 13

## UiPath.PDF.Activities.LocalizedCategoryAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.PDF.Activities.LocalizedDescriptionAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Description : String [Plain]

## UiPath.PDF.Activities.LocalizedDisplayNameAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - DisplayName : String [Plain]

## UiPath.PDF.Activities.PDF.ExportPDFPageAsImage
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FileName** : String [In]  // NomeDoArquivo
  - **ImageDpi** : UiPath.PDF.ImageDpi [Plain]  // DpiDaImagem
  - **PageNumber** : Int32 [In]  // NúmeroDaPágina
  - **OutputFileName** : String [In]  // NomeDoArquivoDeSaída
- optional:
  - InFilter : String [Plain]
  - Password : String [In]  // Senha
  - OutFilter : String [Plain]
  - SaveTitle : String [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.PDF.Activities.PDF.ExtractImagesFromPDF
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FileName** : String [In]  // NomeDoArquivo
  - **ImageExtension** : UiPath.PDF.ImageExtension [Plain]  // ExtensãoDaImagem
  - **OutputFolderName** : String [In]  // NomeDaPastaDeSaída
- optional:
  - Filter : String [Plain]
  - OpenTitle : String [Plain]
  - Password : String [In]  // Senha
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.PDF.Activities.PDF.ExtractPDFPageRange
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FileName** : String [In]  // NomeDoArquivo
  - **Range** : String [In]  // Intervalo
  - **OutputFileName** : String [In]  // NomeDoArquivoDeSaída
- optional:
  - InFilter : String [Plain]
  - Password : String [In]  // Senha
  - OutFilter : String [Plain]
  - SaveTitle : String [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.PDF.Activities.PDF.GetPDFPageCount
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FileName** : String [In]  // NomeDoArquivo
- optional:
  - Filter : String [Plain]
  - OpenTitle : String [Plain]
  - Password : String [In]  // Senha
  - PageCount : Int32 [Out]  // ContagemDePáginas
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.PDF.Activities.PDF.JoinPDF
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FileList** : String[] [In]  // ListaDeArquivos
  - **OutputFileName** : String [In]  // NomeDoArquivoDeSaída
- optional:
  - Filter : String [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.PDF.Activities.PDF.ManagePDFPassword
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FileName** : String [In]  // NomeDoArquivo
  - **OutputFileName** : String [In]  // NomeDoArquivoDeSaída
- optional:
  - InFilter : String [Plain]
  - OutFilter : String [Plain]
  - OldUserPassword : String [In]  // SenhaAntigaDoUsuário
  - NewUserPassword : String [In]  // NovaSenhaDoUsuário
  - OldOwnerPassword : String [In]  // SenhaAntigaDoProprietário
  - NewOwnerPassword : String [In]  // NovaSenhaDoProprietário
  - SaveTitle : String [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.PDF.Activities.ReadPDFText
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FileName** : String [In]  // NomeDoArquivo
- optional:
  - PreserveFormatting : Boolean [In] = false  // PreservarFormatação
  - Filter : String [Plain]
  - OpenTitle : String [Plain]
  - Password : String [In]  // Senha
  - Range : String [In]  // Intervalo
  - Text : String [Out]  // Texto
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.PDF.Activities.ReadPDFWithOCR
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **ImageDpi** : UiPath.PDF.ImageDpi [Plain]  // DpiDaImagem
  - **FileName** : String [In]  // NomeDoArquivo
  - **DegreeOfParallelism** : Int32 [In]  // GrauDeParalelismo
- optional:
  - Filter : String [Plain]
  - OpenTitle : String [Plain]
  - Range : String [In]  // Intervalo
  - Text : String [Out]  // Texto
  - Password : String [In]  // Senha
  - OCREngine : Activities.ActivityFunc<Drawing.Image,Collections.Generic.IEnumerable<Collections.Generic.KeyValuePair<Drawing.Rectangle,String>>> [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.XPS.Activities.ReadXPSText
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FileName** : String [In]  // NomeDoArquivo
- optional:
  - Filter : String [Plain]
  - OpenTitle : String [Plain]
  - Password : String [In]  // Senha
  - Range : String [In]  // Intervalo
  - Text : String [Out]  // Texto
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.XPS.Activities.ReadXPSWithOCR
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FileName** : String [In]  // NomeDoArquivo
  - **DegreeOfParallelism** : Int32 [In]  // GrauDeParalelismo
- optional:
  - Filter : String [Plain]
  - OpenTitle : String [Plain]
  - Range : String [In]  // Intervalo
  - Text : String [Out]  // Texto
  - Password : String [In]  // Senha
  - OCREngine : Activities.ActivityFunc<Drawing.Image,Collections.Generic.IEnumerable<Collections.Generic.KeyValuePair<Drawing.Rectangle,String>>> [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

