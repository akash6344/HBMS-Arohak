import { useState, type FormEvent } from 'react'
import { Button, FormField, Input, Stack } from '../../ui'
import styles from './SearchRoomsForm.module.scss'

export interface RoomSearchValues {
  check_in: string
  check_out: string
  guests: number
  city: string
}

interface SearchRoomsFormProps {
  initialValues?: Partial<RoomSearchValues>
  loading?: boolean
  onSubmit: (values: RoomSearchValues) => void
}

export function SearchRoomsForm({ initialValues, loading, onSubmit }: SearchRoomsFormProps) {
  const [values, setValues] = useState<RoomSearchValues>({
    check_in: initialValues?.check_in ?? '',
    check_out: initialValues?.check_out ?? '',
    guests: initialValues?.guests ?? 2,
    city: initialValues?.city ?? 'Mumbai',
  })

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    onSubmit(values)
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <div className={styles.grid}>
        <FormField label="Check-in" htmlFor="check_in">
          <Input
            id="check_in"
            type="date"
            required
            value={values.check_in}
            onChange={(event) => setValues((prev) => ({ ...prev, check_in: event.target.value }))}
          />
        </FormField>
        <FormField label="Check-out" htmlFor="check_out">
          <Input
            id="check_out"
            type="date"
            required
            value={values.check_out}
            onChange={(event) => setValues((prev) => ({ ...prev, check_out: event.target.value }))}
          />
        </FormField>
        <FormField label="Guests" htmlFor="guests">
          <Input
            id="guests"
            type="number"
            min={1}
            max={20}
            required
            value={values.guests}
            onChange={(event) =>
              setValues((prev) => ({ ...prev, guests: Number(event.target.value) }))
            }
          />
        </FormField>
        <FormField label="City" htmlFor="city">
          <Input
            id="city"
            value={values.city}
            onChange={(event) => setValues((prev) => ({ ...prev, city: event.target.value }))}
          />
        </FormField>
      </div>
      <Stack direction="horizontal">
        <Button type="submit" loading={loading}>
          Search availability
        </Button>
      </Stack>
    </form>
  )
}
