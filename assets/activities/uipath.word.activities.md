# uipath.word.activities
Assembly: UiPath.Word.Activities v2.2.0.0
PackageVersion: 2.2.0
ActivityCount: 25

## UiPath.Word.Activities.DocumentAddImage
- xmlns: `http://schemas.uipath.com/workflow/activities/word`
- required:
  - **ImagePath** : String [In]  // Imagem a inserir
  - **FilePath** : String [In]  @group=File  // Caminho do arquivo
  - **PathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=PathResource  // File
- optional:
  - Text : String [In]  // Texto
  - Bookmark : String [In]  // Indicador
  - OccurrenceIndex : Nullable<Int32> [In]  // ÍndiceDeOcorrências
  - Occurrence : UiPath.Word.Occurrence [Plain] = 0  // Ocorrência
  - Position : UiPath.Word.Position [Plain]  // Posição
  - InsertRelativeTo : UiPath.Word.InsertRelativeType [Plain]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Word.Activities.DocumentAppendText
- xmlns: `http://schemas.uipath.com/workflow/activities/word`
- required:
  - **Text** : String [In]  // Texto
  - **FilePath** : String [In]  @group=File  // Caminho do arquivo
  - **PathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=PathResource  // File
- optional:
  - NewLine : Boolean [Plain] = true  // Nova linha
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Word.Activities.DocumentInsertDataTable
- xmlns: `http://schemas.uipath.com/workflow/activities/word`
- required:
  - **DataTable** : Data.DataTable [In]  // TabelaDeDados
  - **FilePath** : String [In]  @group=File  // Caminho do arquivo
  - **PathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=PathResource  // File
- optional:
  - Text : String [In]  // Texto
  - Bookmark : String [In]  // Indicador
  - OccurrenceIndex : Nullable<Int32> [In]  // ÍndiceDeOcorrências
  - Occurrence : UiPath.Word.Occurrence [Plain] = 0  // Ocorrência
  - Position : UiPath.Word.Position [Plain]  // Posição
  - InsertRelativeTo : UiPath.Word.InsertRelativeType [Plain]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Word.Activities.DocumentInsertHyperlink
- xmlns: `http://schemas.uipath.com/workflow/activities/word`
- required:
  - **TextToDisplay** : String [In]  // Text to display
  - **Address** : String [In]  // Address
  - **FilePath** : String [In]  @group=File  // Caminho do arquivo
  - **PathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=PathResource  // File
- optional:
  - TextToSearchFor : String [In]  // Text to search for
  - InsertRelativeTo : UiPath.Word.InsertHyperlinkRelativeToType [Plain]  // The location relative to which to insert the hyperlink.
  - Position : UiPath.Word.Position [Plain]  // Posição onde inserir
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Word.Activities.DocumentReadText
- xmlns: `http://schemas.uipath.com/workflow/activities/word`
- required:
  - **FilePath** : String [In]  @group=File  // Caminho do arquivo
  - **PathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=PathResource  // File
- optional:
  - Text : String [Out]  // Texto
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Word.Activities.DocumentReplacePicture
- xmlns: `http://schemas.uipath.com/workflow/activities/word`
- required:
  - **PicturePath** : String [In]  // Substituir por imagem
  - **PictureAltText** : String [In]  // Localizar imagens com texto Alt
  - **FilePath** : String [In]  @group=File  // Caminho do arquivo
  - **PathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=PathResource  // File
- optional:
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Word.Activities.DocumentReplaceText
- xmlns: `http://schemas.uipath.com/workflow/activities/word`
- required:
  - **Search** : String [In]  // Pesquisar
  - **Replace** : String [In]  // Replace
  - **FilePath** : String [In]  @group=File  // Caminho do arquivo
  - **PathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=PathResource  // File
- optional:
  - Found : Boolean [Out]  // Localizado
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Word.Activities.DocumentSetBookmarkContent
- xmlns: `http://schemas.uipath.com/workflow/activities/word`
- required:
  - **BookmarkName** : String [In]  // Nome do indicador
  - **BookmarkText** : String [In]  // Texto do indicador
  - **FilePath** : String [In]  @group=File  // Caminho do arquivo
  - **PathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=PathResource  // File
- optional:
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Word.Activities.LocalizedCategoryAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities/word`

## UiPath.Word.Activities.LocalizedDescriptionAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities/word`
- optional:
  - Description : String [Plain]

## UiPath.Word.Activities.LocalizedDisplayNameAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities/word`
- optional:
  - DisplayName : String [Plain]

## UiPath.Word.Activities.WordAddImage
- xmlns: `http://schemas.uipath.com/workflow/activities/word`
- required:
  - **ImagePath** : String [In]  // Imagem a inserir
- optional:
  - Text : String [In]  // Texto
  - Bookmark : String [In]  // Indicador
  - OccurrenceIndex : Nullable<Int32> [In]  // ÍndiceDeOcorrências
  - Occurrence : UiPath.Word.Occurrence [Plain] = 0  // Ocorrência
  - Position : UiPath.Word.Position [Plain]  // Posição
  - InsertRelativeTo : UiPath.Word.InsertRelativeType [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Word.Activities.WordAddSensitivityLabel
- xmlns: `http://schemas.uipath.com/workflow/activities/word`
- required:
  - **SensitivityLabel** : Object [In]  // Rótulo de confidencialidade
- optional:
  - Justification : String [In]  // Justificativa
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Word.Activities.WordAppendText
- xmlns: `http://schemas.uipath.com/workflow/activities/word`
- required:
  - **Text** : String [In]  // Texto
- optional:
  - NewLine : Boolean [Plain] = true  // Nova linha
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Word.Activities.WordApplicationScope
- xmlns: `http://schemas.uipath.com/workflow/activities/word`
- required:
  - **FilePath** : String [In]  // Caminho do arquivo
- optional:
  - Body : Activities.ActivityAction<UiPath.Word.WordDocument> [Plain]
  - CreateNewFile : Boolean [Plain] = true  // Criar se não existir
  - AutoSave : Boolean [Plain] = true  // Salvar automaticamente
  - ReadOnly : Boolean [Plain] = false  // SomenteLeitura
  - SensitivityOperation : UiPath.Word.WordLabelOperation [Plain]  // Operação de confidencialidade
  - SensitivityLabel : Object [In]  // Rótulo de confidencialidade
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Word.Activities.WordExportToPdf
- xmlns: `http://schemas.uipath.com/workflow/activities/word`
- required:
  - **FilePath** : String [In]  // Caminho do arquivo
- optional:
  - ReplaceExisting : Boolean [Plain] = true  // Substituir existente
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Word.Activities.WordGetSensitivityLabel
- xmlns: `http://schemas.uipath.com/workflow/activities/word`
- optional:
  - SensitivityLabel : UiPath.Word.IWordLabelObject [Out]  // Rótulo de confidencialidade
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Word.Activities.WordInsertDataTable
- xmlns: `http://schemas.uipath.com/workflow/activities/word`
- required:
  - **DataTable** : Data.DataTable [In]  // TabelaDeDados
- optional:
  - Position : UiPath.Word.Position [Plain]
  - Text : String [In]  // Texto
  - Bookmark : String [In]  // Indicador
  - OccurrenceIndex : Nullable<Int32> [In]  // ÍndiceDeOcorrências
  - Occurrence : UiPath.Word.Occurrence [Plain] = 0  // Ocorrência
  - InsertRelativeTo : UiPath.Word.InsertRelativeType [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Word.Activities.WordInsertHyperlink
- xmlns: `http://schemas.uipath.com/workflow/activities/word`
- required:
  - **TextToDisplay** : String [In]  // Text to display
  - **Address** : String [In]  // Address
- optional:
  - TextToSearchFor : String [In]  // Text to search for
  - InsertRelativeTo : UiPath.Word.InsertHyperlinkRelativeToType [Plain]  // The location relative to which to insert the hyperlink.
  - Position : UiPath.Word.Position [Plain]  // Posição onde inserir
  - Found : Boolean [Out]  // Localizado
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Word.Activities.WordPasteFromClipboard
- xmlns: `http://schemas.uipath.com/workflow/activities/word`
- optional:
  - PasteRelativeTo : UiPath.Word.PasteRelativeToType [Plain]  // Paste relative to
  - Position : UiPath.Word.Position [Plain]  // Posição onde colar
  - PasteOption : UiPath.Word.PasteOptionType [Plain]  // Opção para colar
  - Text : String [In]  // Texto
  - Found : Boolean [Out]  // Localizado
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Word.Activities.WordReadText
- xmlns: `http://schemas.uipath.com/workflow/activities/word`
- required:
  - **Text** : String [Out]  // Texto
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Word.Activities.WordReplacePicture
- xmlns: `http://schemas.uipath.com/workflow/activities/word`
- required:
  - **PicturePath** : String [In]  // Substituir por imagem
  - **PictureAltText** : String [In]  // Localizar imagens com texto Alt
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Word.Activities.WordReplaceText
- xmlns: `http://schemas.uipath.com/workflow/activities/word`
- required:
  - **Search** : String [In]  // Pesquisar
  - **Replace** : String [In]  // Substituir
- optional:
  - ReplaceAll : Boolean [Plain]  // Substituir tudo
  - Found : Boolean [Out]  // Localizado
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Word.Activities.WordSaveAs
- xmlns: `http://schemas.uipath.com/workflow/activities/word`
- required:
  - **FilePath** : String [In]  // Salvar como arquivo
- optional:
  - SaveAsFileType : UiPath.Word.WordSaveAsType [Plain] = 0  // Salvar como tipo
  - ReplaceExisting : Boolean [Plain] = true  // Substituir existente
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Word.Activities.WordSetBookmarkContent
- xmlns: `http://schemas.uipath.com/workflow/activities/word`
- required:
  - **BookmarkName** : String [In]  // Nome do indicador
  - **BookmarkText** : String [In]  // Texto do indicador
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

