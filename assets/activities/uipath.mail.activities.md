# uipath.mail.activities
Assembly: UiPath.Mail.Activities v2.0.11.0
PackageVersion: 2.0.11
ActivityCount: 50

## UiPath.Mail.Activities.Business.ArchiveMailX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **MailMessage** : Net.Mail.MailMessage [In]  // Email
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Activities.Business.CreateHtmlContent
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **HtmlContent** : String [Out]  // Conteúdo HTML
- optional:
  - HtmlContentArg : UiPath.Mail.Activities.Business.HtmlEditor.HtmlContentArgument [Plain]  // Argumento do Conteúdo HTML
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Activities.Business.DeleteMailX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **MailMessage** : Net.Mail.MailMessage [In]  // Email
- optional:
  - PermanentlyDelete : Boolean [Plain] = false  // Excluir permanentemente
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Activities.Business.ExchangeApplicationCard
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - ApplicationId : String [In]  // Application Id
  - TenantId : String [In]  // IdDoTenant
  - EmailAddress : String [In]  // Email
  - SharedMailbox : String [Plain]  // Caixa de correio compartilhada a usar
  - Account : String [Plain]
  - Connector : String [Plain]
  - ConnectionAccountName : String [Plain]
  - ConnectionId : String [In]  // Conexão
  - BindingsKey : String [Plain]
  - UseConnectionService : Boolean [Plain]  // Usar Integration Service
  - BindingsVersion : String [Plain]
  - Body : Activities.ActivityAction<UiPath.Mail.IMailQuickHandle> [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Activities.Business.ForEachEmailX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Mails** : Collections.Generic.IEnumerable<Net.Mail.MailMessage> [In]  // Em emails de
- optional:
  - Body : Activities.ActivityAction<Net.Mail.MailMessage,Int32> [Plain]
  - UnreadOnly : Boolean [Plain]  // Apenas não lidos
  - WithAttachmentsOnly : Boolean [Plain]  // Apenas com anexos
  - IncludeSubfolders : Boolean [Plain]  // Incluir subpastas
  - RetrieveAttachments : Boolean [Plain] = true  // RecuperarAnexos
  - MailFilter : UiPath.Mail.Activities.Business.ForEachMail.MailFilterArgument [Plain]
  - NumberOfEmailsLimit : Int32 [Plain]  // Limitar emails aos primeiros
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Activities.Business.ForwardMailX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **MailMessage** : Net.Mail.MailMessage [In]  // Email
  - **To** : String [In]  // Adicionar destinatários a Para
- optional:
  - Cc : String [In]  // Adicionar destinatários a Cc
  - Bcc : String [In]  // Adicionar destinatários a Cco
  - NewSubject : String [In]  // Novo assunto
  - OnBehalfOf : String [In]  // Enviar em nome de
  - Files : Collections.Generic.List<Activities.InArgument<String>> [Plain]  // Anexos
  - IsDraft : Boolean [Plain] = true  // Salvar como rascunho
  - Body : String [In]  // Corpo
  - BodyDocumentPath : String [In]  // Caminho do documento do corpo
  - MaxBodyDocumentSizeMB : Double [Plain]  // Tamanho Máx do Documento do Corpo
  - BodyType : UiPath.Mail.Activities.Utils.MailBodyType [Plain] = 0  // Tipo de corpo
  - HtmlBodyFromFile : UiPath.Mail.Activities.Business.HtmlEditor.HtmlContentArgument [Plain]  // Corpo HTML do arquivo
  - HtmlBodyFromText : String [In]  // Corpo HTML do texto
  - UseDocumentAsBody : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Activities.Business.GetEmailById
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Account** : UiPath.Mail.IMailQuickHandle [In]  // Conta
  - **EmailId** : String [In]  // ID do Email
- optional:
  - Result : Net.Mail.MailMessage [Out]  // Referenciar como
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Activities.Business.GmailApplicationCard
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Account : String [Plain]
  - EmailAddress : String [In]  // Email
  - ClientId : String [In]  // IdDoCliente
  - ClientSecret : String [In]  // SegredoDoCliente
  - Timeout : Double [In]  // Tempo limite
  - Connector : String [Plain]
  - ConnectionAccountName : String [Plain]
  - ConnectionId : String [In]  // Conexão
  - BindingsKey : String [Plain]
  - UseConnectionService : Boolean [Plain]  // Usar Integration Service
  - BindingsVersion : String [Plain]
  - Body : Activities.ActivityAction<UiPath.Mail.IMailQuickHandle> [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Activities.Business.MarkMailAsReadX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **MailMessage** : Net.Mail.MailMessage [In]  // Email
- optional:
  - MarkAs : UiPath.Mail.Activities.Business.MarkMailAs [Plain]  // Marcar como
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Activities.Business.MoveMailX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **MailMessage** : Net.Mail.MailMessage [In]  // Email
  - **MailFolder** : String [In]  // Mover para
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Activities.Business.NewGmailTrigger
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Operation : String [Plain]
  - ObjectName : String [Plain]
  - Connector : String [Plain]
  - ConnectionAccountName : String [Plain]
  - ConnectionId : String [In]  // Conexão
  - Result : Net.Mail.MailMessage [Out]  // Email recebido
  - FilterExpression : String [Plain]
  - UiPathEventConnector : String [In]
  - UiPathEvent : String [In]
  - UiPathEventObjectType : String [In]
  - UiPathEventObjectId : String [In]
  - UseConnectionService : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Activities.Business.NewO365EmailTrigger
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Operation : String [Plain]
  - ObjectName : String [Plain]
  - Connector : String [Plain]
  - ConnectionAccountName : String [Plain]
  - ConnectionId : String [In]  // Conexão
  - Result : Net.Mail.MailMessage [Out]  // Email recebido
  - FilterExpression : String [Plain]
  - UiPathEventConnector : String [In]
  - UiPathEvent : String [In]
  - UiPathEventObjectType : String [In]
  - UiPathEventObjectId : String [In]
  - UseConnectionService : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Activities.Business.OutlookApplicationCard
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Account : String [Plain]  // Conta
  - AccountMismatchBehavior : UiPath.Mail.Activities.Business.AccountMismatchBehavior [Plain]  // Comportamento de incompatibilidade de conta
  - Body : Activities.ActivityAction<UiPath.Mail.IMailQuickHandle> [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Activities.Business.OutlookForEachMail
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Mails** : Collections.Generic.IEnumerable<Net.Mail.MailMessage> [In]  // Em emails de
- optional:
  - Body : Activities.ActivityAction<Net.Mail.MailMessage,Int32> [Plain]
  - UnreadOnly : Boolean [Plain]  // Apenas não lidos
  - WithAttachmentsOnly : Boolean [Plain]  // Apenas com anexos
  - IncludeSubfolders : Boolean [Plain]  // Incluir subpastas
  - RetrieveAttachments : Boolean [Plain] = true  // RecuperarAnexos
  - MailFilter : UiPath.Mail.Activities.Business.ForEachMail.MailFilterArgument [Plain]
  - NumberOfEmailsLimit : Int32 [Plain]  // Limitar emails aos primeiros
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Activities.Business.ReplyToMailX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **MailMessage** : Net.Mail.MailMessage [In]  // Email
- optional:
  - AdditionalTo : String [In]  // Adicionar destinatários a Para
  - AdditionalCc : String [In]  // Adicionar destinatários a Cc
  - Bcc : String [In]  // Adicionar destinatários a Cco
  - NewSubject : String [In]  // Novo assunto
  - ReplyToAll : Boolean [Plain]  // Responder a todos
  - Files : Collections.Generic.List<Activities.InArgument<String>> [Plain]  // Anexos
  - IsDraft : Boolean [Plain] = true  // Salvar como rascunho
  - Body : String [In]  // Corpo
  - BodyDocumentPath : String [In]  // Caminho do documento do corpo
  - MaxBodyDocumentSizeMB : Double [Plain]  // Tamanho Máx do Documento do Corpo
  - BodyType : UiPath.Mail.Activities.Utils.MailBodyType [Plain] = 0  // Tipo de corpo
  - HtmlBodyFromFile : UiPath.Mail.Activities.Business.HtmlEditor.HtmlContentArgument [Plain]  // Corpo HTML do arquivo
  - HtmlBodyFromText : String [In]  // Corpo HTML do texto
  - UseDocumentAsBody : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Activities.Business.SaveMailAttachmentsX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Message** : Net.Mail.MailMessage [In]  // Email
- optional:
  - FolderPath : String [In]  // Salvar na pasta
  - Filter : String [In]  // Filtrar por nome de arquivo
  - ExcludeInlineAttachments : Boolean [Plain]  // Excluir Anexos Incorporados
  - Attachments : Collections.Generic.IEnumerable<String> [Out]  // Anexos
  - OverwriteExisting : Boolean [Plain]  // Substituir existente
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Activities.Business.SaveMailX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **MailMessage** : Net.Mail.MailMessage [In]  // Email
- optional:
  - FolderPath : String [In]  // Salvar na pasta
  - FileName : String [In]  // Nome do arquivo
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Activities.Business.SendCalendarInviteX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Account** : UiPath.Mail.IMailQuickHandle [In]  // Conta
  - **StartDate** : DateTime [In]  // Data de início
  - **StartTime** : DateTime [In]  // Hora de início
  - **AlertInterval** : TimeSpan [In]  // Lembrete
- optional:
  - Subject : String [In]  // Título/assunto
  - RequiredAttendees : String [In]  // Participantes obrigatórios
  - OptionalAttendees : String [In]  // Participantes opcionais
  - Duration : TimeSpan [In]  // Duração
  - AllDayEvent : Boolean [Plain]  // Evento de dia inteiro
  - SaveWithoutSending : Boolean [Plain]  // Salvar sem enviar
  - Location : String [In]  // Localização
  - Description : String [In]  // Descrição
  - BusyStatus : UiPath.Mail.Implementation.AppointmentBusyStatus [Plain]  // Mostrar como
  - UseDocumentAsBody : Boolean [Plain] = false  // Documento do Word
  - BodyDocumentPath : String [In]  // Caminho do documento do corpo
  - MaxBodyDocumentSizeMB : Double [Plain]  // Tamanho Máx do Documento do Corpo
  - Files : Collections.Generic.List<Activities.InArgument<String>> [Plain]  // Anexos
  - IsRecurring : Boolean [Plain]  // É recorrente
  - EndDate : DateTime [In]  // Data de término
  - RecurrenceTotalOccurrences : Int32 [In]  // Total de ocorrências recorrentes
  - RecurrenceEndType : UiPath.Mail.Implementation.RecurrenceEndType [Plain]  // Tipo final de recorrência
  - RecurrencePatternType : UiPath.Mail.Implementation.RecurrencePatternType [Plain]  // Tipo de padrão de recorrência
  - DailyRecurrenceType : UiPath.Mail.Implementation.DailyRecurrenceType [Plain]  // Tipo de recorrência diária
  - DailyRecurrenceStep : Int32 [In]  // Etapa de recorrência diária
  - WeeklyRecurrenceStep : Int32 [In]  // Etapa de recorrência semanal
  - WeeklyRecurrenceDays : UiPath.Mail.Implementation.WeekDays [Plain]  // Dias de recorrência semanal
  - MonthlyRecurrenceType : UiPath.Mail.Implementation.MonthlyRecurrenceType [Plain]  // Tipo de recorrência mensal
  - MonthlyRecurrenceDayIndex : Int32 [In]  // Índice de dias de recorrência mensal
  - MonthlyRecurrenceStep : Int32 [In]  // Etapa de recorrência mensal
  - MonthlyRecurrenceWeek : UiPath.Mail.Implementation.RecurrenceInstance [Plain]  // Semana de recorrência mensal
  - MonthlyRecurrenceDay : UiPath.Mail.Implementation.WeekDayType [Plain]  // Dia de recorrência mensal
  - YearlyRecurrenceType : UiPath.Mail.Implementation.YearlyRecurrenceType [Plain]  // Tipo de recorrência anual
  - YearlyRecurrenceStep : Int32 [In]  // Etapa de recorrência anual
  - YearlyRecurrenceMonth : UiPath.Mail.Implementation.Month [Plain]  // Mês de recorrência anual
  - YearlyRecurrenceDayIndex : Int32 [In]  // Índice de dias de recorrência anual
  - YearlyRecurrenceWeek : UiPath.Mail.Implementation.RecurrenceInstance [Plain]  // Semana de recorrência anual
  - YearlyRecurrenceDay : UiPath.Mail.Implementation.WeekDayType [Plain]  // Dia de recorrência anual
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Activities.Business.SendMailX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Account** : UiPath.Mail.IMailQuickHandle [In]  // Conta
  - **To** : String [In]  // Para
- optional:
  - Cc : String [In]  // CC
  - Bcc : String [In]  // CCO
  - Subject : String [In]  // Assunto
  - Files : Collections.Generic.List<Activities.InArgument<String>> [Plain]  // Anexos
  - IsDraft : Boolean [Plain] = true  // Salvar como rascunho
  - ReplyTo : String [In]  // Reply to
  - Importance : UiPath.Mail.MailImportance [Plain]  // Importância
  - Sensitivity : UiPath.Mail.MailSensitivity [Plain]  // Confidencialidade
  - Body : String [In]  // Corpo
  - BodyDocumentPath : String [In]  // Caminho do documento do corpo
  - MaxBodyDocumentSizeMB : Double [Plain]  // Tamanho Máx do Documento do Corpo
  - BodyType : UiPath.Mail.Activities.Utils.MailBodyType [Plain] = 0  // Tipo de corpo
  - HtmlBodyFromFile : UiPath.Mail.Activities.Business.HtmlEditor.HtmlContentArgument [Plain]  // Corpo HTML do arquivo
  - HtmlBodyFromText : String [In]  // Corpo HTML do texto
  - UseDocumentAsBody : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Activities.GetMailMessageFromFile
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - EmailFile : UiPath.Platform.ResourceHandling.IResource [In]
  - MailMessage : UiPath.Mail.UiPathMailMessage [Out]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Activities.LocalizedCategoryAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Mail.Activities.LocalizedDescriptionAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Description : String [Plain]

## UiPath.Mail.Activities.LocalizedDisplayNameAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - DisplayName : String [Plain]

## UiPath.Mail.Activities.SaveMail
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - MailMessage : Net.Mail.MailMessage [In]  // Mail message
  - FilePath : String [In]  // CaminhoDoArquivo
  - Email : UiPath.Platform.ResourceHandling.ILocalResource [Out]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Activities.SaveMailAttachments
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - FolderPath : String [In]  // CaminhoDaPasta
  - Message : Net.Mail.MailMessage [In]  // Mensagem
  - Attachments : Collections.Generic.IEnumerable<String> [Out]  // Anexos
  - ResourceAttachments : Collections.Generic.IEnumerable<UiPath.Platform.ResourceHandling.ILocalResource> [Out]
  - Filter : String [In]  // Filtro
  - OverwriteExisting : Boolean [In]  // SubstituirExistente
  - ExcludeInlineAttachments : Boolean [In]  // Excluir Anexos Incorporados
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Exchange.Activities.CreateDraft
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Name : String [In]  // Nome
  - From : String [In]  // De
  - To : String [In]  // Para
  - Cc : String [In]  // CC
  - Bcc : String [In]  // CCO
  - Subject : String [In]  // Assunto
  - Body : String [In]  // Corpo
  - MailMessage : Net.Mail.MailMessage [In]  // Mail message
  - IsBodyHtml : Boolean [Plain]  // ÉCorpoEmHTML
  - Files : Collections.Generic.List<Activities.InArgument<String>> [Plain]  // Anexos
  - AttachmentsCollection : Collections.Generic.IEnumerable<String> [In]
  - ResourceAttachments : Collections.Generic.IEnumerable<UiPath.Platform.ResourceHandling.IResource> [In]
  - ResourceAttachmentList : Collections.Generic.IEnumerable<Activities.InArgument<UiPath.Platform.ResourceHandling.IResource>> [Plain]
  - AttachmentInputMode : UiPath.MicrosoftOffice365.Activities.Mail.Enums.AttachmentInputMode [Plain]
  - AttachmentsBackup : UiPath.Shared.Activities.Utils.BackupSlot<UiPath.MicrosoftOffice365.Activities.Mail.Enums.AttachmentInputMode> [Plain]
  - Server : String [In]  @group=Server  // Servidor
  - ExchangeVersion : Microsoft.Exchange.WebServices.Data.ExchangeVersion [Plain]  // VersãoDoExchange
  - EmailAutodiscover : String [In]  @group=AutoDiscover  // DescobertaAutomáticaDeEmail
  - ApplicationId : String [In]  // Application Id
  - DirectoryId : String [In]  // DirectoryId
  - AuthenticationMode : UiPath.Mail.Exchange.AuthenticationType [Plain]  // AuthenticationType
  - User : String [In]  // Usuário
  - Password : String [In]  // Senha
  - SecurePassword : Security.SecureString [In]  // Senha Segura
  - Domain : String [In]  // Domínio
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Exchange.Activities.DeleteMail
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **MailMessage** : Net.Mail.MailMessage [In]  // Mail message
- optional:
  - DeleteMode : Microsoft.Exchange.WebServices.Data.DeleteMode [Plain]  // ExcluirModo
  - Server : String [In]  @group=Server  // Servidor
  - ExchangeVersion : Microsoft.Exchange.WebServices.Data.ExchangeVersion [Plain]  // VersãoDoExchange
  - EmailAutodiscover : String [In]  @group=AutoDiscover  // DescobertaAutomáticaDeEmail
  - ApplicationId : String [In]  // Application Id
  - DirectoryId : String [In]  // DirectoryId
  - AuthenticationMode : UiPath.Mail.Exchange.AuthenticationType [Plain]  // AuthenticationType
  - User : String [In]  // Usuário
  - Password : String [In]  // Senha
  - SecurePassword : Security.SecureString [In]  // Senha Segura
  - Domain : String [In]  // Domínio
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Exchange.Activities.ExchangeScope
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Server** : String [In]  @group=Server  // Servidor
  - **EmailAutodiscover** : String [In]  @group=AutoDiscover  // DescobertaAutomáticaDeEmail
- optional:
  - ExchangeVersion : Microsoft.Exchange.WebServices.Data.ExchangeVersion [Plain]  // VersãoDoExchange
  - ApplicationId : String [In]  // Application Id
  - DirectoryId : String [In]  // DirectoryId
  - AuthenticationMode : UiPath.Mail.Exchange.AuthenticationType [Plain]  // AuthenticationType
  - ExistingExchangeService : Microsoft.Exchange.WebServices.Data.ExchangeService [In]  @group=Existing Connection  // Serviço Existente do Exchange
  - User : String [In]  // Usuário
  - Password : String [In]  // Senha
  - SecurePassword : Security.SecureString [In]  // Senha Segura
  - Domain : String [In]  // Domínio
  - ExchangeService : Microsoft.Exchange.WebServices.Data.ExchangeService [Out]  // ServiçoDoExchange
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - Body : Activities.ActivityAction<Microsoft.Exchange.WebServices.Data.ExchangeService> [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Exchange.Activities.GetExchangeMailMessages
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - MailFolder : Microsoft.Exchange.WebServices.Data.WellKnownFolderName [Plain] = 4  // Mail folder
  - CustomFolder : String [In]  // Mail folder
  - SharedMailbox : String [In]  // CaixaDeCorreioCompartilhada
  - GetAttachements : Boolean [Plain]  // ObterAnexos
  - IsBodyHtml : Boolean [Plain]  // ÉCorpoEmHTML
  - Top : Int32 [In]  // Superior
  - OnlyUnreadMessages : Boolean [Plain]  // Only unread messages
  - MarkAsRead : Boolean [Plain]  // Mark as read
  - FilterExpression : String [In]  // The filter expression to be used.
  - FilterByMessageIds : String[] [In]  // Filter by message ids
  - OrderByDate : UiPath.Mail.EOrderByDate [Plain]  // Order by date
  - Messages : Collections.Generic.List<Net.Mail.MailMessage> [Out]  // Mensagens
  - Server : String [In]  @group=Server  // Servidor
  - ExchangeVersion : Microsoft.Exchange.WebServices.Data.ExchangeVersion [Plain]  // VersãoDoExchange
  - EmailAutodiscover : String [In]  @group=AutoDiscover  // DescobertaAutomáticaDeEmail
  - ApplicationId : String [In]  // Application Id
  - DirectoryId : String [In]  // DirectoryId
  - AuthenticationMode : UiPath.Mail.Exchange.AuthenticationType [Plain]  // AuthenticationType
  - User : String [In]  // Usuário
  - Password : String [In]  // Senha
  - SecurePassword : Security.SecureString [In]  // Senha Segura
  - Domain : String [In]  // Domínio
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Exchange.Activities.MoveMessageToFolder
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **MailMessage** : Net.Mail.MailMessage [In]  // Mail message
  - **MailFolder** : String [In]  // Mail folder
- optional:
  - SharedMailbox : String [In]  // CaixaDeCorreioCompartilhada
  - Server : String [In]  @group=Server  // Servidor
  - ExchangeVersion : Microsoft.Exchange.WebServices.Data.ExchangeVersion [Plain]  // VersãoDoExchange
  - EmailAutodiscover : String [In]  @group=AutoDiscover  // DescobertaAutomáticaDeEmail
  - ApplicationId : String [In]  // Application Id
  - DirectoryId : String [In]  // DirectoryId
  - AuthenticationMode : UiPath.Mail.Exchange.AuthenticationType [Plain]  // AuthenticationType
  - User : String [In]  // Usuário
  - Password : String [In]  // Senha
  - SecurePassword : Security.SecureString [In]  // Senha Segura
  - Domain : String [In]  // Domínio
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Exchange.Activities.SaveExchangeAttachements
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - FolderPath : String [In]  // CaminhoDaPasta
  - MailMessage : Net.Mail.MailMessage [In]  // Mail message
  - Files : Collections.Generic.IEnumerable<String> [Out]  // Arquivos
  - ResourceAttachments : Collections.Generic.IEnumerable<UiPath.Platform.ResourceHandling.ILocalResource> [Out]
  - Server : String [In]  @group=Server  // Servidor
  - ExchangeVersion : Microsoft.Exchange.WebServices.Data.ExchangeVersion [Plain]  // VersãoDoExchange
  - EmailAutodiscover : String [In]  @group=AutoDiscover  // DescobertaAutomáticaDeEmail
  - ApplicationId : String [In]  // Application Id
  - DirectoryId : String [In]  // DirectoryId
  - AuthenticationMode : UiPath.Mail.Exchange.AuthenticationType [Plain]  // AuthenticationType
  - User : String [In]  // Usuário
  - Password : String [In]  // Senha
  - SecurePassword : Security.SecureString [In]  // Senha Segura
  - Domain : String [In]  // Domínio
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Exchange.Activities.SendExchangeMail
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **To** : String [In]  // Para
- optional:
  - Cc : String [In]  // CC
  - Bcc : String [In]  // CCO
  - Subject : String [In]  // Assunto
  - Body : String [In]  // Corpo
  - IsBodyHtml : Boolean [Plain]  // ÉCorpoEmHTML
  - MailMessage : Net.Mail.MailMessage [In]  // Mail message
  - Name : String [In]  // Nome
  - From : String [In]  // De
  - SaveCopy : Boolean [Plain]  // SalvarCópia
  - Attachments : Collections.Generic.List<String> [Plain]
  - Files : Collections.Generic.List<Activities.InArgument<String>> [Plain]  // Anexos
  - AttachmentsCollection : Collections.Generic.IEnumerable<String> [In]  // Attachments collection
  - ResourceAttachments : Collections.Generic.IEnumerable<UiPath.Platform.ResourceHandling.IResource> [In]
  - ResourceAttachmentList : Collections.Generic.IEnumerable<Activities.InArgument<UiPath.Platform.ResourceHandling.IResource>> [Plain]
  - AttachmentInputMode : UiPath.MicrosoftOffice365.Activities.Mail.Enums.AttachmentInputMode [Plain]
  - AttachmentsBackup : UiPath.Shared.Activities.Utils.BackupSlot<UiPath.MicrosoftOffice365.Activities.Mail.Enums.AttachmentInputMode> [Plain]
  - IsDraft : Boolean [Plain]  // Is draft
  - Server : String [In]  @group=Server  // Servidor
  - ExchangeVersion : Microsoft.Exchange.WebServices.Data.ExchangeVersion [Plain]  // VersãoDoExchange
  - EmailAutodiscover : String [In]  @group=AutoDiscover  // DescobertaAutomáticaDeEmail
  - ApplicationId : String [In]  // Application Id
  - DirectoryId : String [In]  // DirectoryId
  - AuthenticationMode : UiPath.Mail.Exchange.AuthenticationType [Plain]  // AuthenticationType
  - User : String [In]  // Usuário
  - Password : String [In]  // Senha
  - SecurePassword : Security.SecureString [In]  // Senha Segura
  - Domain : String [In]  // Domínio
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.IMAP.Activities.DeleteImapMailMessage
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - UseOAuth : Boolean [In]  // UsarOAuth
  - Email : String [In]  // Email
  - Password : String [In]  @group=Password  // Senha
  - SecurePassword : Security.SecureString [In]  @group=SecurePassword  // Senha Segura
  - Server : String [In]  // Servidor
  - Port : Int32 [In]  // Porta
  - SecureConnection : UiPath.Mail.SecureSocketEncryption [Plain]  // ConexãoSegura
  - ClientName : String [In]  // Nome do cliente
  - ClientVersion : String [In]  // VersãoDoCliente
  - IgnoreCRL : Boolean [In] = false  // Ignorar CRL
  - MailMessage : Net.Mail.MailMessage [In]
  - FromFolder : String [In]
  - ConnectionId : String [Plain]  // Conexão
  - ConnectionMode : UiPath.Mail.Activities.Enums.ConnectionDetails [Plain]
  - UseISConnection : Boolean [Plain]
  - ConnectionDetailsBackupSlot : UiPath.Shared.Activities.Utils.BackupSlot<UiPath.Mail.Activities.Enums.ConnectionDetails> [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.IMAP.Activities.GetIMAPMailMessages
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - UseOAuth : Boolean [In]  // UsarOAuth
  - Email : String [In]  // Email
  - Password : String [In]  @group=Password  // Senha
  - SecurePassword : Security.SecureString [In]  @group=SecurePassword  // Senha Segura
  - Server : String [In]  // Servidor
  - Port : Int32 [In]  // Porta
  - EnableSSL : Boolean [Plain]  // HabilitarSSL
  - MailFolder : String [In]  // Mail folder
  - FilterExpression : String [In]  // FiltrarExpressão
  - FilterExpressionCharacterSet : String [In]  // FiltrarConjuntoDeCaracteresDaExpressão
  - OrderByDate : UiPath.Mail.EOrderByDate [Plain]  // OrdernarPorData
  - DeleteMessages : Boolean [In]  // ExcluirMensagens
  - OnlyUnreadMessages : Boolean [In]  // Only unread messages
  - MarkAsRead : Boolean [In]  // Mark as read
  - SecureConnection : UiPath.Mail.SecureSocketEncryption [Plain]  // ConexãoSegura
  - ClientName : String [In]  // Nome do cliente
  - ClientVersion : String [In]  // VersãoDoCliente
  - IgnoreCRL : Boolean [In] = false  // Ignorar CRL
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - Top : Int32 [In]  // Superior
  - Messages : Collections.Generic.List<Net.Mail.MailMessage> [Out]  // Mensagens
  - ConnectionId : String [Plain]  // Conexão
  - ConnectionMode : UiPath.Mail.Activities.Enums.ConnectionDetails [Plain]
  - UseISConnection : Boolean [Plain]
  - ConnectionDetailsBackupSlot : UiPath.Shared.Activities.Utils.BackupSlot<UiPath.Mail.Activities.Enums.ConnectionDetails> [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.IMAP.Activities.MoveIMAPMailMessageToFolder
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - UseOAuth : Boolean [In]  // UsarOAuth
  - Email : String [In]  // Email
  - Password : String [In]  @group=Password  // Senha
  - SecurePassword : Security.SecureString [In]  @group=SecurePassword  // Senha Segura
  - Server : String [In]  // Servidor
  - Port : Int32 [In]  // Porta
  - EnableSSL : Boolean [Plain]  // HabilitarSSL
  - MailMessage : Net.Mail.MailMessage [In]  // Mail message
  - MailFolder : String [In]  // Mail folder
  - FromFolder : String [In]  // DaPasta
  - SecureConnection : UiPath.Mail.SecureSocketEncryption [Plain]  // ConexãoSegura
  - ClientName : String [In]  // NomeDoCliente
  - ClientVersion : String [In]  // VersãoDoCliente
  - IgnoreCRL : Boolean [In] = false  // Ignorar CRL
  - ConnectionId : String [Plain]  // Conexão
  - ConnectionMode : UiPath.Mail.Activities.Enums.ConnectionDetails [Plain]
  - UseISConnection : Boolean [Plain]
  - ConnectionDetailsBackupSlot : UiPath.Shared.Activities.Utils.BackupSlot<UiPath.Mail.Activities.Enums.ConnectionDetails> [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.LotusNotes.Activities.DeleteLotusNotesMailMessage
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **MailMessage** : Net.Mail.MailMessage [In]  // Mail message
  - **FromFolder** : String [In]  // DaPasta
- optional:
  - Password : String [In]  @group=Password  // Senha
  - SecurePassword : Security.SecureString [In]  @group=SecurePassword  // Senha Segura
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.LotusNotes.Activities.GetLotusNotesMailMessages
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **MailFolder** : String [In]  // Mail folder
- optional:
  - Password : String [In]  @group=Password  // Senha
  - SecurePassword : Security.SecureString [In]  @group=SecurePassword  // Senha Segura
  - GetAttachments : Boolean [Plain]  // ObterAnexos
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - Top : Int32 [In]  // Superior
  - Messages : Collections.Generic.List<Net.Mail.MailMessage> [Out]  // Mensagens
  - ConnectionId : String [Plain]  // Conexão
  - ConnectionMode : UiPath.Mail.Activities.Enums.ConnectionDetails [Plain]
  - UseISConnection : Boolean [Plain]
  - ConnectionDetailsBackupSlot : UiPath.Shared.Activities.Utils.BackupSlot<UiPath.Mail.Activities.Enums.ConnectionDetails> [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.LotusNotes.Activities.MoveLotusNotesMailMessage
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **MailMessage** : Net.Mail.MailMessage [In]  // Mail message
  - **MailFolder** : String [In]  // Mail folder
  - **FromFolder** : String [In]  // DaPasta
- optional:
  - Password : String [In]  @group=Password  // Senha
  - SecurePassword : Security.SecureString [In]  @group=SecurePassword  // Senha Segura
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.LotusNotes.Activities.SendLotusNotesMailMessage
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **To** : String [In]  // Para
- optional:
  - Password : String [In]  // Senha
  - SecurePassword : Security.SecureString [In]  // Senha Segura
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Cc : String [In]  // CC
  - Bcc : String [In]  // CCO
  - Subject : String [In]  // Assunto
  - Body : String [In]  // Corpo
  - IsBodyHtml : Boolean [Plain]  // ÉCorpoEmHTML
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - Files : Collections.Generic.List<Activities.InArgument<String>> [Plain]  // Anexos
  - AttachmentsCollection : Collections.Generic.IEnumerable<String> [In]  // Attachments collection
  - MailMessage : Net.Mail.MailMessage [In]  @group=Forward  // Mail message
  - ConnectionId : String [Plain]  // Conexão
  - ConnectionMode : UiPath.Mail.Activities.Enums.ConnectionDetails [Plain]
  - UseISConnection : Boolean [Plain]
  - ConnectionDetailsBackupSlot : UiPath.Shared.Activities.Utils.BackupSlot<UiPath.Mail.Activities.Enums.ConnectionDetails> [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Outlook.Activities.DeleteOutlookMailMessage
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **MailMessage** : Net.Mail.MailMessage [In]  // Mail message
- optional:
  - PermanentlyDelete : Boolean [Plain]  // Permanently delete
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Outlook.Activities.GetOutlookMailMessages
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **MailFolder** : String [In]  // Mail folder
- optional:
  - KnownFolder : UiPath.Mail.KnownFolders [Plain] = 0  // PastaConhecida
  - Account : String [In]  // Conta
  - Filter : String [In]  // Filtro
  - FilterByMessageIds : String[] [In]  // Filter by message ids
  - OrderByDate : UiPath.Mail.EOrderByDate [Plain]  // Order by date
  - GetAttachements : Boolean [Plain]  // ObterAnexos
  - OnlyUnreadMessages : Boolean [Plain]  // Only unread messages
  - MarkAsRead : Boolean [Plain]  // Mark as read
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - Top : Int32 [In]  // Superior
  - Messages : Collections.Generic.List<Net.Mail.MailMessage> [Out]  // Mensagens
  - ConnectionId : String [Plain]  // Conexão
  - ConnectionMode : UiPath.Mail.Activities.Enums.ConnectionDetails [Plain]
  - UseISConnection : Boolean [Plain]
  - ConnectionDetailsBackupSlot : UiPath.Shared.Activities.Utils.BackupSlot<UiPath.Mail.Activities.Enums.ConnectionDetails> [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Outlook.Activities.MarkOutlookMailAsRead
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **MailMessage** : Net.Mail.MailMessage [In]  // Email
- optional:
  - MarkAs : UiPath.Mail.Activities.Business.MarkMailAs [Plain]  // Mark as
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Outlook.Activities.MoveOutlookMessage
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **MailMessage** : Net.Mail.MailMessage [In]  // Mail message
  - **MailFolder** : String [In]  // Mail folder
- optional:
  - Account : String [In]  // Conta
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Outlook.Activities.ReplyToOutlookMailMessage
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **MailMessage** : Net.Mail.MailMessage [In]  // Mail message
- optional:
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - ReplyAll : Boolean [Plain]  // Reply all
  - Body : String [In]  // Corpo
  - Files : Collections.Generic.List<Activities.InArgument<String>> [Plain]  // Anexos
  - AttachmentsCollection : Collections.Generic.IEnumerable<String> [In]  // Attachments collection
  - Importance : UiPath.Mail.MailImportance [Plain]  // Importância
  - ReplyFrom : String [In]  // Reply from
  - AddTo : String [In]  // Para
  - AddCc : String [In]  // CC
  - AddBcc : String [In]  // CCO
  - NewSubject : String [In]  // New subject
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Outlook.Activities.SaveOutlookAttachements
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - FolderPath : String [In]  // CaminhoDaPasta
  - Account : String [In]  // Conta
  - MailMessage : Net.Mail.MailMessage [In]  // Mail message
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Outlook.Activities.SaveOutlookMailMessage
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **MailMessage** : Net.Mail.MailMessage [In]  // Mail message
  - **Folder** : String [In]  // Pasta
- optional:
  - FileName : String [In]  // File name
  - ReplaceExisting : Boolean [Plain]  // Replace existing
  - SaveAsType : UiPath.Mail.Outlook.Enums.ESaveMessageAsType [Plain]  // Save as type
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Outlook.Activities.SendOutlookMail
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **To** : String [In]  // Para
- optional:
  - Attachments : Collections.Generic.List<String> [Plain]
  - Account : String [In]  // Conta
  - SentOnBehalfOfName : String [In]  // Send on behalf of
  - IsDraft : Boolean [Plain]  // Is draft
  - ReplyTo : String [In]  // Reply to
  - Importance : UiPath.Mail.MailImportance [Plain]  // Importância
  - Sensitivity : UiPath.Mail.MailSensitivity [Plain]  // Confidencialidade
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Cc : String [In]  // CC
  - Bcc : String [In]  // CCO
  - Subject : String [In]  // Assunto
  - Body : String [In]  // Corpo
  - IsBodyHtml : Boolean [Plain]  // ÉCorpoEmHTML
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - Files : Collections.Generic.List<Activities.InArgument<String>> [Plain]  // Anexos
  - AttachmentsCollection : Collections.Generic.IEnumerable<String> [In]  // Attachments collection
  - MailMessage : Net.Mail.MailMessage [In]  @group=Forward  // Mail message
  - ConnectionId : String [Plain]  // Conexão
  - ConnectionMode : UiPath.Mail.Activities.Enums.ConnectionDetails [Plain]
  - UseISConnection : Boolean [Plain]
  - ConnectionDetailsBackupSlot : UiPath.Shared.Activities.Utils.BackupSlot<UiPath.Mail.Activities.Enums.ConnectionDetails> [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.Outlook.Activities.SetOutlookMailCategories
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **MailMessage** : Net.Mail.MailMessage [In]  // Email
- optional:
  - Categories : String[] [In]  // Categorias
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.POP3.Activities.GetPOP3MailMessages
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - UseOAuth : Boolean [In]  // UsarOAuth
  - Email : String [In]  // Email
  - Password : String [In]  @group=Password  // Senha
  - SecurePassword : Security.SecureString [In]  @group=SecurePassword  // Senha Segura
  - Server : String [In]  // Servidor
  - Port : Int32 [In]  // Porta
  - EnableSSL : Boolean [Plain]  // HabilitarSSL
  - DeleteMessages : Boolean [In]  // ExcluirMensagens
  - SecureConnection : UiPath.Mail.SecureSocketEncryption [Plain]  // ConexãoSegura
  - IgnoreCRL : Boolean [In] = false  // Ignorar CRL
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - Top : Int32 [In]  // Superior
  - Messages : Collections.Generic.List<Net.Mail.MailMessage> [Out]  // Mensagens
  - ConnectionId : String [Plain]  // Conexão
  - ConnectionMode : UiPath.Mail.Activities.Enums.ConnectionDetails [Plain]
  - UseISConnection : Boolean [Plain]
  - ConnectionDetailsBackupSlot : UiPath.Shared.Activities.Utils.BackupSlot<UiPath.Mail.Activities.Enums.ConnectionDetails> [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Mail.SMTP.Activities.SendMail
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **To** : String [In]  // Para
- optional:
  - UseOAuth : Boolean [In]  // UsarOAuth
  - Email : String [In]  // Email
  - Password : String [In]  // Senha
  - SecurePassword : Security.SecureString [In]  // Senha Segura
  - Server : String [In]  // Servidor
  - Port : Int32 [In]  // Porta
  - EnableSSL : Boolean [Plain]  // HabilitarSSL
  - Name : String [In]  // Nome
  - From : String [In]  // De
  - Attachments : Collections.Generic.List<String> [Plain]
  - ResourceAttachments : Collections.Generic.IEnumerable<UiPath.Platform.ResourceHandling.IResource> [In]
  - ResourceAttachmentList : Collections.Generic.IEnumerable<Activities.InArgument<UiPath.Platform.ResourceHandling.IResource>> [Plain]
  - AttachmentInputMode : UiPath.MicrosoftOffice365.Activities.Mail.Enums.AttachmentInputMode [Plain]
  - AttachmentsBackup : UiPath.Shared.Activities.Utils.BackupSlot<UiPath.MicrosoftOffice365.Activities.Mail.Enums.AttachmentInputMode> [Plain]
  - SecureConnection : UiPath.Mail.SecureSocketEncryption [Plain]  // ConexãoSegura
  - ReplyTo : String [In]  // Responder a
  - IgnoreCRL : Boolean [In] = false  // Ignorar CRL
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Result : String [Out]  // Código do Status
  - Cc : String [In]  // CC
  - Bcc : String [In]  // CCO
  - Subject : String [In]  // Assunto
  - Body : String [In]  // Corpo
  - IsBodyHtml : Boolean [Plain]  // ÉCorpoEmHTML
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - Files : Collections.Generic.List<Activities.InArgument<String>> [Plain]  // Anexos
  - AttachmentsCollection : Collections.Generic.IEnumerable<String> [In]  // Attachments collection
  - MailMessage : Net.Mail.MailMessage [In]  @group=Forward  // Mail message
  - ConnectionId : String [Plain]  // Conexão
  - ConnectionMode : UiPath.Mail.Activities.Enums.ConnectionDetails [Plain]
  - UseISConnection : Boolean [Plain]
  - ConnectionDetailsBackupSlot : UiPath.Shared.Activities.Utils.BackupSlot<UiPath.Mail.Activities.Enums.ConnectionDetails> [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

