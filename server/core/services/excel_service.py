import pandas as pd
from django.db import transaction
from core.models import CertificateBatch, Certificate, Participant
import uuid
from core.validators import validate_file_content, sanitize_text

def analyze_excel_file(file_path):
    """Analyze any Excel file at a path and return headers, preview, and suggested mapping."""
    try:
        df = pd.read_excel(file_path, dtype=str, nrows=5)
        columns = [str(c).strip() for c in df.columns]

        suggestions = {}
        original_cols_lower = {c.lower(): c for c in columns}

        def find_match(keywords, exclude=None):
            for k in keywords:
                for col_lower in original_cols_lower:
                    if exclude and any(ex in col_lower for ex in exclude):
                        continue
                    if k in col_lower:
                        return original_cols_lower[col_lower]
            return None

        suggestions['cedula'] = find_match(['cedula', 'dni', 'identidad', 'documento', 'identificación'], exclude=['nombre', 'apellido', 'participante'])
        suggestions['nombres'] = find_match(['nombres', 'nombre', 'participante', 'estudiante'])
        suggestions['apellidos'] = find_match(['apellidos', 'apellido'])
        suggestions['email'] = find_match(['email', 'correo', 'e-mail', 'mail'])
        suggestions['celular'] = find_match(['celular', 'telefono', 'movil', 'whatsapp', 'tlf'])
        suggestions['curso'] = find_match(['curso', 'seminario', 'tema', 'capacitacion'])

        preview = df.fillna('').values.tolist()

        return {
            'success': True,
            'columns': columns,
            'suggestions': suggestions,
            'preview': preview,
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def analyze_excel_headers(lote_id):
    """Analyze the Excel file attached to a Batch."""
    try:
        batch = CertificateBatch.objects.get(id=lote_id)
        return analyze_excel_file(batch.excel_file.path)
    except CertificateBatch.DoesNotExist:
        return {'success': False, 'error': 'Lote no encontrado.'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def procesar_archivo_excel_lote_business(lote_id, mapping=None):
    """
    Business logic to process an Excel file for a Batch.
    Recieves optional 'mapping' dict: {'cedula': 'ColName', 'nombres': 'ColName', ...}
    """
    try:
        with transaction.atomic():
            batch = CertificateBatch.objects.select_for_update().get(id=lote_id)
            if batch.certificates.exists():
                return False, "Este lote ya ha sido procesado anteriormente y ya contiene certificados."

            file_path = batch.excel_file.path
            
            # Read Excel
            df = pd.read_excel(file_path, dtype=str)
            
            # Clean headers/columns: strip whitespace
            df.columns = [str(c).strip() for c in df.columns]
            
            created_count = 0
            nombre_lote_upper = batch.name.upper().strip()
            nombre_lote_upper = batch.name.upper().strip()
            curso_context = nombre_lote_upper
            
            # ---------------------------------------------------------
            # Column Determination
            # ---------------------------------------------------------
            col_cedula = mapping.get('cedula') if mapping else None
            col_nombres = mapping.get('nombres') if mapping else None
            col_apellidos = mapping.get('apellidos') if mapping else None
            col_email = mapping.get('email') if mapping else None
            col_celular = mapping.get('celular') if mapping else None
            col_curso = mapping.get('curso') if mapping else None
            
            # Auto-detect if no mapping provided (Legacy support)
            if not mapping:
                for c in df.columns:
                    cl = c.lower()
                    if not col_nombres and ('nombre' in cl or 'participante' in cl): col_nombres = c
                    if not col_email and ('correo' in cl or 'email' in cl): col_email = c
                    if not col_cedula and ('cedula' in cl or 'dni' in cl or 'identidad' in cl): col_cedula = c
            
            # ---------------------------------------------------------
            # Row Processing
            # ---------------------------------------------------------
            certificates_to_create = []
            procesados_en_excel = set() # (cedula, email, curso) to prevent intra-file duplicates
            
            for index, row in df.iterrows():
                # Extract Data using Mapping
                
                # 1. Cedula
                cedula_raw = ""
                if col_cedula and col_cedula in df.columns:
                    cedula_raw = sanitize_text(str(row[col_cedula]))
                
                # 2. Email (Mandatory & Lowercase)
                email_raw = ""
                if col_email and col_email in df.columns:
                    email_raw = sanitize_text(str(row[col_email])).lower().strip()
                
                # 3. Nombres & Apellidos Logic
                nombre_raw = ""
                apellido_raw = ""
                
                if col_nombres and col_nombres in df.columns:
                    nombre_raw = sanitize_text(str(row[col_nombres]))
                    
                if col_apellidos and col_apellidos in df.columns:
                    apellido_raw = sanitize_text(str(row[col_apellidos]))

                # 4. Celular
                celular_raw = ""
                if col_celular and col_celular in df.columns:
                    # Sanitize: Keep only digits
                    val = str(row[col_celular])
                    if val.lower() != 'nan':
                        nums = ''.join(filter(str.isdigit, val))
                        
                        # Logic: 10 digits starting with 0
                        if len(nums) == 10 and nums.startswith('0'):
                            celular_raw = nums
                        
                        # Logic: 9 digits (missing leading zero) -> Prepend 0
                        elif len(nums) == 9:
                            celular_raw = f"0{nums}"
                            
                        # Else: Invalid (too short, too long, or weird format) -> Leave empty
                
                # Cleanup NaNs / Empty Strings
                if nombre_raw.lower() == 'nan': nombre_raw = ""
                if apellido_raw.lower() == 'nan': apellido_raw = ""
                if cedula_raw.lower() == 'nan': cedula_raw = ""
                if email_raw.lower() == 'nan': email_raw = ""
                if celular_raw.lower() == 'nan': celular_raw = ""

                # SKIP VALIDATION: Email is Mandatory
                if not email_raw:
                    continue # Skip this row if no email
                    
                # Cedula Cleanup
                cedula = cedula_raw
                if cedula.endswith('.0'): cedula = cedula[:-2]
                if not cedula: cedula = f"GEN-{uuid.uuid4().hex[:8].upper()}"

                # Name Parsing / Splitting
                final_nombres = "PARTICIPANTE"
                final_apellidos = "S/N"
                
                if apellido_raw:
                    # Explicit columns
                    final_nombres = nombre_raw
                    final_apellidos = apellido_raw
                elif nombre_raw:
                    # Split Full Name
                    parts = nombre_raw.split()
                    if len(parts) >= 2:
                        if len(parts) == 2:
                            final_nombres = parts[0]
                            final_apellidos = parts[1]
                        elif len(parts) == 3:
                            final_nombres = parts[0]
                            final_apellidos = f"{parts[1]} {parts[2]}"
                        else: 
                            mid = len(parts) // 2
                            final_nombres = " ".join(parts[:mid])
                            final_apellidos = " ".join(parts[mid:])
                    else:
                        final_nombres = nombre_raw
                        
                # Custom Course Name from Column?
                final_curso = curso_context
                if col_curso and col_curso in df.columns:
                    val = str(row[col_curso]).strip()
                    if val and val.lower() != 'nan':
                        final_curso = val.upper()

                # Create or find Participante for deduplication
                participante = None
                is_generated_cedula = cedula.startswith('GEN-') or not cedula
                real_cedula = '' if is_generated_cedula else cedula

                # Check if this exact combination was already processed in this file
                unique_key = (real_cedula, email_raw, final_curso)
                if unique_key in procesados_en_excel:
                    continue # Skip duplicates within the excel file
                procesados_en_excel.add(unique_key)

                if real_cedula:
                    participante = Participant.objects.filter(national_id=real_cedula).first()
                if not participante and email_raw:
                    participante = Participant.objects.filter(email__iexact=email_raw).first()

                if participante:
                    # Update missing fields
                    updated = []
                    if real_cedula and not participante.national_id:
                        participante.national_id = real_cedula
                        updated.append('national_id')
                    if celular_raw and not participante.phone:
                        participante.phone = celular_raw
                        updated.append('phone')
                    if updated:
                        participante.save(update_fields=updated)
                else:
                    participante = Participant.objects.create(
                        national_id=real_cedula,
                        first_name=final_nombres.upper(),
                        last_name=final_apellidos.upper(),
                        email=email_raw,
                        phone=celular_raw,
                    )

                certificates_to_create.append(Certificate(
                    batch=batch,
                    participant=participante,
                    national_id=cedula,
                    first_name=final_nombres.upper(),
                    last_name=final_apellidos.upper(),
                    email=email_raw,
                    phone=celular_raw,
                    course=final_curso,
                    verification_hash=uuid.uuid4()
                ))
                created_count += 1
            

            # Bulk Create for performance
            if certificates_to_create:
                # We need to save first to get IDs if needed, but for sending email we have the objects.
                # However, bulk_create on SQLite/Postgres returns objects with IDs.
                created_certs = Certificate.objects.bulk_create(certificates_to_create)

                # Enviar el MISMO correo branded que usa todo el aplicativo
                # (plantilla + cuenta institucional por Gmail API), de forma
                # asíncrona y solo DESPUÉS de confirmar la transacción, para que
                # el worker vea los certificados ya guardados. El encolado va en
                # try/except: si el broker falla, no debe colgar ni romper la carga.
                from core.tasks.email_tasks import send_certificate_issued_bulk

                def _dispatch_emails(bid=batch.id):
                    try:
                        send_certificate_issued_bulk.delay(batch_id=bid)
                    except Exception as e:
                        print(f"No se pudo encolar correos del lote {bid}: {e}")

                transaction.on_commit(_dispatch_emails)
                
            return True, f"Se procesaron {created_count} participantes exitosamente."

    except Exception as e:

        print(f"Error processing Excel in business layer: {e}")
        return False, str(e)


# English aliases for clean imports
process_excel_batch = procesar_archivo_excel_lote_business
analyze_headers = analyze_excel_headers
