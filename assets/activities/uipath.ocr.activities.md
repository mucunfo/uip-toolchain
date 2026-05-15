# uipath.ocr.activities
Assembly: UiPath.OCR.Activities v3.24.0.0
PackageVersion: 3.24.0
ActivityCount: 8

## UiPath.OCR.Activities.CjkOCR
- xmlns: `http://schemas.uipath.com/workflow/activities/ocr`
- required:
  - **Image** : Drawing.Image [In]  // Imagem
  - **Timeout** : Int32 [In]  // Tempo Limite (milissegundos)
- optional:
  - Endpoint : String [In]  // Ponto de extremidade
  - ApiKey : String [In]  // ChaveDaAPI
  - UseSeparateOcrProcess : Boolean [In]  // UsarProcessoDeOCRSeparado
  - Profile : UiPath.Vision.OCR.OCRProfile [Plain]
  - ComputeSkewAngle : Boolean [Plain]
  - Language : String [In]
  - ExtractWords : Boolean [Plain]
  - Scale : Double [In]
  - Text : String [Out]  // Texto
  - NoopExecution : Boolean [Plain]
  - PredictionId : String [In]
  - Output : UiPath.OCR.Contracts.OcrActivityResult [Out]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.OCR.Activities.CjkOCRProxyClient
- xmlns: `http://schemas.uipath.com/workflow/activities/ocr`

## UiPath.OCR.Activities.ExtendedLanguagesOCR
- xmlns: `http://schemas.uipath.com/workflow/activities/ocr`
- required:
  - **Image** : Drawing.Image [In]  // Imagem
  - **Timeout** : Int32 [In]  // Tempo Limite (milissegundos)
- optional:
  - Endpoint : String [In]  // Ponto de extremidade
  - ApiKey : String [In]  // ChaveDaAPI
  - UseSeparateOcrProcess : Boolean [In]  // UsarProcessoDeOCRSeparado
  - Profile : UiPath.Vision.OCR.OCRProfile [Plain]
  - ComputeSkewAngle : Boolean [Plain]
  - Language : String [In]
  - ExtractWords : Boolean [Plain]
  - Scale : Double [In]
  - Text : String [Out]  // Texto
  - NoopExecution : Boolean [Plain]
  - PredictionId : String [In]
  - Output : UiPath.OCR.Contracts.OcrActivityResult [Out]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.OCR.Activities.LocalizedCategoryAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities/ocr`

## UiPath.OCR.Activities.LocalizedDescriptionAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities/ocr`
- optional:
  - Description : String [Plain]

## UiPath.OCR.Activities.LocalizedDisplayNameAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities/ocr`
- optional:
  - DisplayName : String [Plain]

## UiPath.OCR.Activities.UiPathDocumentOCR
- xmlns: `http://schemas.uipath.com/workflow/activities/ocr`
- required:
  - **Image** : Drawing.Image [In]  // Imagem
  - **Timeout** : Int32 [In]  // Tempo Limite (milissegundos)
- optional:
  - Profile : UiPath.Vision.OCR.OCRProfile [Plain]
  - Endpoint : String [In]  // Ponto de extremidade
  - ApiKey : String [In]  // ChaveDaAPI
  - UseLocalServer : Boolean [In]  // UsarServidorLocal
  - UseSeparateOcrProcess : Boolean [In]  // UsarProcessoDeOCRSeparado
  - UseAccents : Boolean [In]
  - ComputeSkewAngle : Boolean [Plain]
  - Language : String [In]
  - ExtractWords : Boolean [Plain]
  - Scale : Double [In]
  - Text : String [Out]  // Texto
  - NoopExecution : Boolean [Plain]
  - PredictionId : String [In]
  - Output : UiPath.OCR.Contracts.OcrActivityResult [Out]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.OCR.Activities.UiPathScreenOCR
- xmlns: `http://schemas.uipath.com/workflow/activities/ocr`
- required:
  - **Image** : Drawing.Image [In]  // Imagem
  - **Timeout** : Int32 [In]  // Tempo Limite (milissegundos)
- optional:
  - Profile : UiPath.Vision.OCR.OCRProfile [Plain]
  - Endpoint : String [In]  // Ponto de extremidade
  - ApiKey : String [In]  // ChaveDaAPI
  - UseAccents : Boolean [In]  // UsarAcentos
  - UseLocalServer : Boolean [In]
  - UseSeparateOcrProcess : Boolean [In]  // UsarProcessoDeOCRSeparado
  - ComputeSkewAngle : Boolean [Plain]
  - Language : String [In]
  - ExtractWords : Boolean [Plain]
  - Scale : Double [In]
  - Text : String [Out]  // Texto
  - NoopExecution : Boolean [Plain]
  - PredictionId : String [In]
  - Output : UiPath.OCR.Contracts.OcrActivityResult [Out]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

