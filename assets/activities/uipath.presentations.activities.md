# uipath.presentations.activities
Assembly: UiPath.Presentations.Activities v2.2.1.0
PackageVersion: 2.2.1
ActivityCount: 47

## UiPath.Presentations.Activities.AddSensitivityLabel
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Presentation** : UiPath.Presentations.Activities.IPresentationQuickHandle [In]  // Apresentação
  - **SensitivityLabel** : Object [In]  // Rótulo de confidencialidade
- optional:
  - Justification : String [In]  // Justificativa
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.ChangeShapeNameModel
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Presentations.Activities.ChangeShapeNameSlideContentModification
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **NewShapeName** : String [In]  // Novo Nome da Forma
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.CopyPasteSlide
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **SourcePresentation** : UiPath.Presentations.Activities.IPresentationQuickHandle [In]  // Apresentação de origem
  - **SlideToCopy** : Int32 [In]  // Slide a copiar
  - **DestinationPresentation** : UiPath.Presentations.Activities.IPresentationQuickHandle [In]  // Apresentação de destino
  - **WhereToInsert** : Int32 [In]  // Onde inserir
- optional:
  - Move : Boolean [Plain]  // Mover
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.DeleteSlide
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Presentation** : UiPath.Presentations.Activities.IPresentationQuickHandle [In]  // Apresentação
  - **DeletePosition** : Int32 [In]  // Número do slide
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.FindAndReplaceTextInPresentation
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Presentation** : UiPath.Presentations.Activities.IPresentationQuickHandle [In]  // Apresentação
  - **SearchFor** : String [In]  // O que localizar
- optional:
  - ReplaceWith : String [In]  // Substituir por
  - MatchCase : Boolean [Plain]  // Diferenciar maiúsculas/minúsculas
  - WholeWordsOnly : Boolean [Plain]  // Só palavras inteiras
  - ReplaceAll : Boolean [Plain]  // Substituir tudo
  - NumberOfReplacements : Int32 [Out]  // Número de substituições
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.FontSizeFormatSlideContentModification
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FontSize** : Int32 [In]  // Tamanho da Fonte
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.FontSizeModificationModel
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Presentations.Activities.FormatSlideContent
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Presentation** : UiPath.Presentations.Activities.IPresentationQuickHandle [In]  // Apresentação
  - **SlideIndex** : Int32 [In]  // Número do slide
  - **ShapeName** : String [In]  // Conteúdo a modificar
- optional:
  - Body : Activities.ActivityAction [Plain]
  - AllowedItemType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.FormatSlideContentDescriptor
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Modifications : Collections.Generic.List<UiPath.Presentations.Activities.IFormatSlideModicationModel> [Plain]

## UiPath.Presentations.Activities.FormatSlideContentModificationType
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Presentations.Activities.GetSensitivityLabel
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Presentation** : UiPath.Presentations.Activities.IPresentationQuickHandle [In]  // Apresentação
- optional:
  - SensitivityLabel : UiPath.Presentations.IPptLabelObject [Out]  // Rótulo de confidencialidade
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.InsertFile
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Presentation** : UiPath.Presentations.Activities.IPresentationQuickHandle [In]  // Apresentação
  - **SlideIndex** : Int32 [In]  // Número do slide
  - **FilePath** : String [In]  // Arquivo a adicionar
- optional:
  - ShapeName : String [In]  // Espaço reservado para conteúdo
  - IconLabel : String [In]  // Rótulo do ícone
  - NewShapeName : String [In]  // Novo nome da forma
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.InsertPositionType
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Presentations.Activities.InsertSlide
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Presentation** : UiPath.Presentations.Activities.IPresentationQuickHandle [In]  // Apresentação
  - **SlideMasterName** : String [In]  // Slide Mestre
  - **LayoutName** : String [In]  // Layout
  - **InsertType** : UiPath.Presentations.Activities.InsertPositionType [Plain]  // Adicionar como
- optional:
  - InsertPosition : Int32 [In]  // Inserir posição
  - InsertedAtPosition : Int32 [Out]  // Salvar novo número de slide como
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.InsertTextInPresentation
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Presentation** : UiPath.Presentations.Activities.IPresentationQuickHandle [In]  // Apresentação
  - **SlideIndex** : Int32 [In]  // Número do slide
  - **ShapeName** : String [In]  // Espaço reservado para conteúdo
  - **Text** : String [In]  // Texto a adicionar
- optional:
  - ClearExistingText : Boolean [Plain]  // Limpar texto existente no espaço reservado para conteúdo
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.PasteIntoSlide
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Presentation** : UiPath.Presentations.Activities.IPresentationQuickHandle [In]  // Apresentação
  - **SlideIndex** : Int32 [In]  // Número do slide
  - **ShapeName** : String [In]  // Espaço reservado para conteúdo
- optional:
  - Left : Nullable<Single> [In]  // Esquerda
  - Top : Nullable<Single> [In]  // Superior
  - Width : Nullable<Single> [In]  // Largura do item
  - Height : Nullable<Single> [In]  // Altura do item
  - NewShapeName : String [In]  // Novo nome da forma
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.PowerPointApplicationScope
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **PresentationPath** : String [In]  // Caminho
- optional:
  - Password : String [In]  // Senha
  - EditPassword : String [In]  // Editar senha
  - Visible : Boolean [Plain] = true  // Visível
  - CreateIfNotExists : Boolean [Plain] = true  // Criar se não existir
  - AutoSave : Boolean [Plain] = true  // Salvar mudanças
  - ReadOnly : Boolean [Plain] = false  // Somente leitura
  - UseThemeFile : Boolean [Plain] = false  // Usar arquivo de modelo
  - TemplatePath : String [In]  // Caminho do modelo do Slide Mestre
  - SensitivityOperation : UiPath.Presentations.PptLabelOperation [Plain]  // Operação de confidencialidade
  - SensitivityLabel : Object [In]  // Rótulo de confidencialidade
  - Body : Activities.ActivityAction<UiPath.Presentations.Activities.IPresentationQuickHandle> [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.PptDocumentAddTextToSlide
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FilePath** : String [In]  @group=File  // Apresentação
  - **PathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=PathResource  // Arquivo
  - **SlideIndex** : Int32 [In]  // Número do slide
  - **ShapeName** : String [In]  // Espaço reservado para conteúdo
  - **Text** : String [In]  // Texto a adicionar
- optional:
  - ClearExistingText : Boolean [Plain]  // Limpe o texto existente no espaço reservado para conteúdo.
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.PptDocumentDeleteSlide
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FilePath** : String [In]  @group=File  // Apresentação
  - **PathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=PathResource  // Arquivo
  - **SlideIndex** : Int32 [In]  // Número do slide
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.PptDocumentFindAndReplaceTextInPresentation
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FilePath** : String [In]  @group=File  // Apresentação
  - **PathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=PathResource  // Arquivo
  - **SearchFor** : String [In]  // O que localizar
- optional:
  - ReplaceWith : String [In]  // Substituir por
  - MatchCase : Boolean [Plain]  // Diferenciar maiúsculas/minúsculas
  - WholeWordsOnly : Boolean [Plain]  // Só palavras inteiras
  - ReplaceAll : Boolean [Plain]  // Substituir tudo
  - NumberOfReplacements : Int32 [Out]  // Número de substituições
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.PptDocumentFormatSlideContent
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Presentation** : String [In]  // Apresentação
  - **SlideNumber** : Int32 [In]  // Número do slide
  - **ContentToModify** : String [In]  // Conteúdo a modificar
- optional:
  - Body : Activities.ActivityAction [Plain]
  - AllowedItemType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.PptDocumentFormatSlideContentDescriptor
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Modifications : Collections.Generic.List<UiPath.Presentations.Activities.ISlideContentModicationModel> [Plain]

## UiPath.Presentations.Activities.PptDocumentInsertSlide
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FilePath** : String [In]  // Apresentação
  - **SlideMasterName** : String [In]  // Slide Mestre
  - **LayoutName** : String [In]  // Layout
  - **InsertType** : UiPath.Presentations.Activities.InsertPositionType [Plain]  // Adicionar como
- optional:
  - InsertPosition : Int32 [In]  // Inserir posição
  - InsertedAtPosition : Int32 [Out]  // Salvar novo número de slide como
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.PptDocumentReplaceShapeWithDataTable
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FilePath** : String [In]  // Apresentação
  - **SlideIndex** : Int32 [In]  // Número do slide
  - **ShapeName** : String [In]  // Espaço reservado para conteúdo
  - **TableToInsert** : Data.DataTable [In]  // Tabela a adicionar
- optional:
  - ExcludeHeaders : Boolean [Plain] = false  // Excluir cabeçalhos de origem
  - AppendMode : UiPath.Presentations.TableAppendMode [Plain]  // Comportamento
  - StartRow : Int32 [Plain]  // Substituir começando pela linha
  - StartColumn : Int32 [Plain]  // Substituir começando pela coluna
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.PptDocumentReplaceShapeWithMedia
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FilePath** : String [In]  // Apresentação
  - **SlideIndex** : Int32 [In]  // Número do slide
  - **ShapeName** : String [In]  // Nome da Forma
  - **Media** : String [In]  // Arquivo de imagem/vídeo
- optional:
  - NewShapeName : String [In]  // Novo Nome da Forma
  - Left : Nullable<Single> [In]  // Esquerda
  - Top : Nullable<Single> [In]  // Superior
  - Width : Nullable<Single> [In]  // Largura do item
  - Height : Nullable<Single> [In]  // Altura do item
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.PptDocumentSlideContentModificationType
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Presentations.Activities.PresentationQuickHandle
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Slide : UiPath.Presentations.Activities.ISlideIndexer [Plain]
  - FilePath : String [Plain]

## UiPath.Presentations.Activities.ReplaceShapeWithDataTable
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Presentation** : UiPath.Presentations.Activities.IPresentationQuickHandle [In]  // Apresentação
  - **SlideIndex** : Int32 [In]  // Número do slide
  - **ShapeName** : String [In]  // Espaço reservado para conteúdo
  - **TableToInsert** : Data.DataTable [In]  // Tabela a adicionar
- optional:
  - ExcludeHeaders : Boolean [Plain] = false  // Excluir cabeçalhos de origem
  - AppendMode : UiPath.Presentations.TableAppendMode [Plain]  // Comportamento
  - StartRow : Int32 [Plain]  // Substituir começando pela linha
  - StartColumn : Int32 [Plain]  // Substituir começando pela coluna
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.ReplaceShapeWithMedia
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Presentation** : UiPath.Presentations.Activities.IPresentationQuickHandle [In]  // Apresentação
  - **SlideIndex** : Int32 [In]  // Número do slide
  - **ShapeName** : String [In]  // Nome da Forma
  - **Media** : String [In]  // Arquivo de imagem/vídeo
- optional:
  - NewShapeName : String [In]  // Novo Nome da Forma
  - Left : Nullable<Single> [In]  // Esquerda
  - Top : Nullable<Single> [In]  // Superior
  - Width : Nullable<Single> [In]  // Largura do item
  - Height : Nullable<Single> [In]  // Altura do item
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.RunMacro
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Presentation** : UiPath.Presentations.Activities.IPresentationQuickHandle [In]  // Nome da apresentação
  - **MacroName** : String [In]  // Nome da macro
- optional:
  - Result : ? [Out]  // Valor retornado
  - Body : Activities.ActivityAction [Plain]
  - AllowedItemType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.RunMacroArgument
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **ArgumentValue** : Object [In]  // Valor do argumento
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.RunMacroDescriptor
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Arguments : Collections.Generic.List<Object> [Plain]

## UiPath.Presentations.Activities.SavePresentationAsPdf
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Presentation** : UiPath.Presentations.Activities.IPresentationQuickHandle [In]  // Apresentação
  - **PdfPath** : String [In]  // Caminho para o PDF de destino
- optional:
  - ReplaceExisting : Boolean [Plain] = true  // Substituir existente
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.SavePresentationFileAs
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Presentation** : UiPath.Presentations.Activities.IPresentationQuickHandle [In]  // Apresentação
  - **FilePath** : String [In]  // Salvar como arquivo
- optional:
  - SaveAsFileType : UiPath.Presentations.PresentationSaveAsType [Plain] = 0  // Salvar como tipo
  - ReplaceExisting : Boolean [Plain] = true  // Substituir existente
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.ShapeChangeNameModel
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Presentations.Activities.ShapeChangeNameSlideContentModification
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **NewShapeName** : String [In]  // Novo Nome da Forma
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.ShapeFontSizeModificationModel
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Presentations.Activities.ShapeFontSizeSlideContentModification
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FontSize** : Int32 [In]  // Tamanho da Fonte
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.ShapeIndexer
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Item : UiPath.Presentations.Activities.IShapeQuickHandle [Plain]

## UiPath.Presentations.Activities.ShapeZOrderModificationModel
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Presentations.Activities.ShapeZOrderSlideContentModification
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Action** : UiPath.Presentations.Activities.ZOrderChangeType [Plain]  // Action
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.SlideIndexer
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Item : UiPath.Presentations.Activities.ISlideQuickHandle [Plain]
  - Count : Int32 [Plain]

## UiPath.Presentations.Activities.ZIndexChangeType
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Presentations.Activities.ZIndexFormatSlideModification
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Action** : UiPath.Presentations.Activities.ZIndexChangeType [Plain]  // Action
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Presentations.Activities.ZIndexModificationModel
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Presentations.Activities.ZOrderChangeType
- xmlns: `http://schemas.uipath.com/workflow/activities`

